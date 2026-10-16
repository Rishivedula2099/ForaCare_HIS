import re
import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.facilities.constants import CURRENCY_CODES, TIMEZONE_CODES, FacilityType

_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,49}$")
_USERNAME = re.compile(r"^[A-Za-z0-9._-]{3,100}$")
_PHONE = re.compile(r"^\+?[0-9][0-9 ()-]{6,19}$")
_POSTAL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 -]{2,11}$")


def _clean(value: str) -> str:
    return " ".join(value.split())


def _upper_code(value: str) -> str:
    value = value.strip().upper()
    if not _CODE.match(value):
        raise ValueError("Use 2-50 letters, digits, '-' or '_'.")
    return value


class OrganizationInput(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _clean(v)

    @field_validator("code")
    @classmethod
    def _code(cls, v: str) -> str:
        return _upper_code(v)


class FacilityInput(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    facility_code: str
    facility_type: FacilityType
    phone: str
    email: EmailStr
    address_line1: str = Field(min_length=3, max_length=200)
    address_line2: str | None = Field(default=None, max_length=200)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    postal_code: str
    timezone: str
    currency: str

    @field_validator("name", "address_line1", "city", "state")
    @classmethod
    def _text(cls, v: str) -> str:
        return _clean(v)

    @field_validator("address_line2")
    @classmethod
    def _line2(cls, v: str | None) -> str | None:
        return (_clean(v) or None) if v else None

    @field_validator("facility_code")
    @classmethod
    def _code(cls, v: str) -> str:
        return _upper_code(v)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        v = v.strip()
        if not _PHONE.match(v):
            raise ValueError("Enter a valid phone number (7-20 digits; may start with +).")
        return v

    @field_validator("postal_code")
    @classmethod
    def _postal(cls, v: str) -> str:
        v = v.strip().upper()
        if not _POSTAL.match(v):
            raise ValueError("Enter a valid postal / PIN code.")
        return v

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        if v not in TIMEZONE_CODES:
            raise ValueError("Choose a time zone from the list.")
        return v

    @field_validator("currency")
    @classmethod
    def _currency(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in CURRENCY_CODES:
            raise ValueError("Choose a currency from the list.")
        return v

    def composed_address(self) -> str:
        lines = [self.address_line1, self.address_line2, f"{self.city}, {self.state} {self.postal_code}"]
        return ", ".join(part for part in lines if part)[:500]


class AdministratorInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    username: str
    email: EmailStr

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _clean(v)

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        v = v.strip()
        if not _USERNAME.match(v):
            raise ValueError("Use 3-100 letters, digits, '.', '_' or '-'.")
        return v


class TenantSetupRequest(BaseModel):
    organization: OrganizationInput
    facility: FacilityInput
    administrator: AdministratorInput
    # Email the activation link as well as showing it to the operator.
    send_activation_email: bool = False


class AvailabilityResult(BaseModel):
    organization_code: bool | None = None
    facility_code: bool | None = None
    username: bool | None = None
    email: bool | None = None


class OptionPair(BaseModel):
    value: str
    label: str


class SetupOptions(BaseModel):
    facility_types: list[OptionPair]
    timezones: list[OptionPair]
    currencies: list[OptionPair]
    email_delivery_available: bool
    default_timezone: str = "Asia/Kolkata"
    default_currency: str = "INR"


class SetupResult(BaseModel):
    tenant_id: uuid.UUID
    tenant_code: str
    tenant_name: str
    facility_id: uuid.UUID
    facility_code: str
    facility_name: str
    facility_type: str
    administrator_id: uuid.UUID
    administrator_username: str
    administrator_email: str
    # Shown to the operator exactly once; only its hash is stored.
    activation_link: str
    activation_expires_hours: int
    activation_email_sent: bool
