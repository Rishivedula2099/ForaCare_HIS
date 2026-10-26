from pydantic import BaseModel, EmailStr, Field


class OnboardingRequestCreate(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    contact_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    facility_type: str | None = Field(default=None, max_length=50)
    message: str | None = Field(default=None, max_length=2000)
    # Honeypot: a real visitor never fills this (hidden field); bots do.
    website: str | None = Field(default=None, max_length=200)
