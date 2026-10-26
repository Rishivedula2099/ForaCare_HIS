"""P10-F02: platform-operator provisioning of a new hospital (tenant), its first
facility and its first administrator - atomically, with duplicate detection
that reports every clash at once."""
import re

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.audit import service as audit_service
from app.modules.auth import mailer, user_tokens
from app.modules.auth.models import User, UserFacilityMembership
from app.modules.facilities.constants import CURRENCIES, FACILITY_TYPES, TIMEZONES
from app.modules.facilities.models import Facility
from app.modules.platform.schemas import (
    AvailabilityResult,
    OptionPair,
    SetupOptions,
    SetupResult,
    TenantSetupRequest,
)
from app.modules.rbac.models import Role
from app.modules.tenants.models import Tenant

DUPLICATE_MESSAGES = {
    "organization.code": "An organisation with this code already exists.",
    "facility.facility_code": "A facility with this code already exists.",
    "administrator.username": "This username is already taken.",
    "administrator.email": "An account with this email address already exists.",
}


def setup_options() -> SetupOptions:
    return SetupOptions(
        facility_types=[OptionPair(value=v, label=l) for v, l in FACILITY_TYPES],
        timezones=[OptionPair(value=v, label=l) for v, l in TIMEZONES],
        currencies=[OptionPair(value=v, label=l) for v, l in CURRENCIES],
        email_delivery_available=mailer.mail_configured(),
    )


def _slug(code: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", code.lower()).strip("-")


async def find_duplicates(
    db: AsyncSession,
    *,
    organization_code: str | None = None,
    facility_code: str | None = None,
    username: str | None = None,
    email: str | None = None,
) -> dict[str, bool]:
    """Maps each supplied field to True when it is ALREADY TAKEN."""
    taken: dict[str, bool] = {}
    if organization_code is not None:
        taken["organization.code"] = (
            await db.execute(
                select(Tenant.id).where(
                    or_(Tenant.code == organization_code, Tenant.slug == _slug(organization_code))
                )
            )
        ).first() is not None
    if facility_code is not None:
        taken["facility.facility_code"] = (
            await db.execute(select(Facility.id).where(Facility.facility_code == facility_code))
        ).first() is not None
    if username is not None:
        taken["administrator.username"] = (
            await db.execute(select(User.id).where(User.username == username))
        ).first() is not None
    if email is not None:
        taken["administrator.email"] = (
            await db.execute(select(User.id).where(func.lower(User.email) == email.lower()))
        ).first() is not None
    return taken


async def check_availability(
    db: AsyncSession,
    *,
    organization_code: str | None,
    facility_code: str | None,
    username: str | None,
    email: str | None,
) -> AvailabilityResult:
    taken = await find_duplicates(
        db,
        organization_code=organization_code.strip().upper() if organization_code else None,
        facility_code=facility_code.strip().upper() if facility_code else None,
        username=username.strip() if username else None,
        email=email.strip() if email else None,
    )

    def free(key: str) -> bool | None:
        return None if key not in taken else not taken[key]

    return AvailabilityResult(
        organization_code=free("organization.code"),
        facility_code=free("facility.facility_code"),
        username=free("administrator.username"),
        email=free("administrator.email"),
    )


def _duplicate_error(fields: list[str]) -> ConflictError:
    return ConflictError(
        "Some of these details are already in use.",
        code="DUPLICATE",
        details=[(field, DUPLICATE_MESSAGES[field]) for field in fields],
    )


async def create_tenant_with_facility(
    db: AsyncSession, payload: TenantSetupRequest, operator: User
) -> SetupResult:
    org, fac, admin = payload.organization, payload.facility, payload.administrator

    role = (await db.execute(select(Role).where(Role.code == "HOSPITAL_ADMIN"))).scalar_one_or_none()
    if role is None:
        raise NotFoundError("The HOSPITAL_ADMIN role is missing. Run `alembic upgrade head`.")

    taken = await find_duplicates(
        db,
        organization_code=org.code,
        facility_code=fac.facility_code,
        username=admin.username,
        email=str(admin.email),
    )
    clashes = [field for field, is_taken in taken.items() if is_taken]
    if clashes:
        raise _duplicate_error(clashes)

    try:
        tenant = Tenant(name=org.name, code=org.code, slug=_slug(org.code))
        db.add(tenant)
        await db.flush()
        facility = Facility(
            tenant_id=tenant.id,
            name=fac.name,
            facility_code=fac.facility_code,
            facility_type=fac.facility_type,
            address=fac.composed_address(),
            phone=fac.phone,
            email=str(fac.email).lower(),
            timezone=fac.timezone,
            currency=fac.currency,
        )
        db.add(facility)
        await db.flush()
        user = User(
            tenant_id=tenant.id,
            facility_id=facility.id,
            username=admin.username,
            email=str(admin.email).lower(),
            full_name=admin.full_name,
            role_id=role.id,
            password_hash=user_tokens.unusable_password_hash(),
            is_active=True,
        )
        db.add(user)
        await db.flush()
        db.add(UserFacilityMembership(user_id=user.id, facility_id=facility.id, is_default=True))
        token = await user_tokens.issue_token(db, user, user_tokens.ACTIVATION, commit=False)
        await audit_service.record_event(
            db,
            action="platform.tenant_created",
            resource_type="tenant",
            resource_id=tenant.id,
            after={
                "tenant_code": tenant.code,
                "facility_code": facility.facility_code,
                "facility_type": facility.facility_type,
                "administrator": user.username,
            },
            commit=False,
        )
        await db.commit()
    except IntegrityError:
        # Lost a race with a concurrent submission: nothing was written.
        await db.rollback()
        raise ConflictError(
            "Another setup using the same codes was just completed. Review the details and try again.",
            code="DUPLICATE",
        ) from None

    link = user_tokens.build_link(user_tokens.ACTIVATION, token)
    emailed = False
    if payload.send_activation_email:
        emailed = await mailer.send_email(
            to=user.email,
            subject="Activate your ForaCare HIS account",
            body=f"Hello {user.full_name},\n\nYour organisation {tenant.name} has been set up. "
            f"Choose your password to activate your administrator account:\n\n{link}\n",
        )
    return SetupResult(
        tenant_id=tenant.id,
        tenant_code=tenant.code,
        tenant_name=tenant.name,
        facility_id=facility.id,
        facility_code=facility.facility_code,
        facility_name=facility.name,
        facility_type=facility.facility_type,
        administrator_id=user.id,
        administrator_username=user.username,
        administrator_email=user.email,
        activation_link=link,
        activation_expires_hours=get_settings().user_token_activation_hours,
        activation_email_sent=emailed,
    )
