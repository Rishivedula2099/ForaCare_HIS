"""P10-B01: creating a tenant, facility and its first administrator without any
shipped credentials.

The only supported way into a fresh production database. The admin is created
with an unusable random password and a single-use activation token; whoever
runs the CLI hands the printed link to the administrator, who then chooses
their own password. Nothing here knows a password, so nothing can be leaked.
"""
import re
from dataclasses import dataclass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.modules.audit import service as audit_service
from app.modules.auth import user_tokens
from app.modules.auth.models import User, UserFacilityMembership
from app.modules.facilities.models import Facility
from app.modules.rbac.models import Role
from app.modules.tenants.models import Tenant

_USERNAME = re.compile(r"^[A-Za-z0-9._-]{3,100}$")
_CODE = re.compile(r"^[A-Za-z0-9_-]{2,50}$")
_EMAIL = TypeAdapter(EmailStr)  # the same check UserOut applies when the account signs in


@dataclass
class ProvisionedAdmin:
    user: User
    tenant: Tenant
    facility: Facility
    tenant_created: bool
    facility_created: bool
    activation_token: str


async def provision_admin(
    db: AsyncSession,
    *,
    tenant_name: str,
    tenant_code: str,
    facility_name: str,
    facility_code: str,
    username: str,
    email: str,
    full_name: str,
    role_code: str = "HOSPITAL_ADMIN",
) -> ProvisionedAdmin:
    if not _CODE.match(tenant_code) or not _CODE.match(facility_code):
        raise AppError("Tenant and facility codes must be 2-50 letters, digits, '-' or '_'.", code="VALIDATION_ERROR")
    if not _USERNAME.match(username):
        raise AppError("Username must be 3-100 letters, digits, '.', '_' or '-'.", code="VALIDATION_ERROR")
    try:
        email = str(_EMAIL.validate_python(email))
    except ValidationError as exc:
        raise AppError("Email address is not valid.", code="VALIDATION_ERROR") from exc

    role = (await db.execute(select(Role).where(Role.code == role_code))).scalar_one_or_none()
    if role is None:
        raise NotFoundError(f"Role {role_code} does not exist. Run `alembic upgrade head` first.")

    taken = await db.execute(
        select(User).where((User.username == username) | (func.lower(User.email) == email.lower()))
    )
    if taken.scalar_one_or_none() is not None:
        raise ConflictError("A user with that username or email already exists.")

    tenant = (await db.execute(select(Tenant).where(Tenant.code == tenant_code))).scalar_one_or_none()
    tenant_created = tenant is None
    if tenant is None:
        tenant = Tenant(name=tenant_name, code=tenant_code, slug=tenant_code.lower().replace("_", "-"))
        db.add(tenant)
        await db.flush()

    facility = (
        await db.execute(select(Facility).where(Facility.facility_code == facility_code))
    ).scalar_one_or_none()
    facility_created = facility is None
    if facility is None:
        facility = Facility(tenant_id=tenant.id, name=facility_name, facility_code=facility_code)
        db.add(facility)
        await db.flush()
    elif facility.tenant_id != tenant.id:
        raise ConflictError("That facility code already belongs to a different tenant.")

    user = User(
        tenant_id=tenant.id,
        facility_id=facility.id,
        username=username,
        email=email.lower(),
        full_name=full_name,
        role_id=role.id,
        password_hash=user_tokens.unusable_password_hash(),
        is_active=True,
    )
    db.add(user)
    await db.flush()
    db.add(UserFacilityMembership(user_id=user.id, facility_id=facility.id, is_default=True))
    await audit_service.record_event(
        db,
        action="auth.user_provisioned",
        resource_type="user",
        resource_id=user.id,
        after={"username": username, "role": role_code, "tenant_created": tenant_created},
        actor_username="bootstrap-cli",
        tenant_id=tenant.id,
        facility_id=facility.id,
        commit=False,
    )
    await db.commit()

    token = await user_tokens.issue_token(db, user, user_tokens.ACTIVATION)
    return ProvisionedAdmin(user, tenant, facility, tenant_created, facility_created, token)
