import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

SignatureLabel = Annotated[str, Field(min_length=1, max_length=40)]
PaperSize = Literal["A4", "A5", "A6", "THERMAL_58", "THERMAL_80", "CUSTOM"]


class DocumentTypeOut(BaseModel):
    code: str
    title: str
    required_permissions: list[str]
    supports_templates: bool = False


class TemplateContent(BaseModel):
    """The layout knobs a template version can set (validated, closed set)."""

    model_config = {"extra": "forbid"}

    header_note: str | None = Field(default=None, max_length=200)
    footer_text: str | None = Field(default=None, max_length=300)
    show_facility_contact: bool = True
    # Overrides the document's default signature lines; None = keep defaults.
    signature_labels: list[SignatureLabel] | None = Field(default=None, max_length=4)
    # Page size in mm; only meaningful (and required) when paper_size is CUSTOM.
    custom_width_mm: float | None = Field(default=None, ge=20, le=300)
    custom_height_mm: float | None = Field(default=None, ge=20, le=300)


def _check_custom_size(paper_size: str, content: "TemplateContent") -> None:
    if paper_size == "CUSTOM":
        if content.custom_width_mm is None or content.custom_height_mm is None:
            raise ValueError("A custom paper size needs custom_width_mm and custom_height_mm.")
    elif content.custom_width_mm is not None or content.custom_height_mm is not None:
        raise ValueError("custom_width_mm / custom_height_mm only apply to the CUSTOM paper size.")


class TemplateVersionOut(BaseModel):
    version_number: int
    paper_size: str
    content: dict
    change_note: str | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TemplateOut(BaseModel):
    id: uuid.UUID
    facility_id: uuid.UUID
    document_type: str
    name: str
    is_active: bool
    active_version_number: int
    paper_size: str
    latest_version_number: int
    created_at: datetime
    updated_at: datetime


class TemplateDetailOut(TemplateOut):
    versions: list[TemplateVersionOut]


class TemplateCreateRequest(BaseModel):
    document_type: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    paper_size: PaperSize = "A4"
    content: TemplateContent = Field(default_factory=TemplateContent)
    change_note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _custom_size(self):
        _check_custom_size(self.paper_size, self.content)
        return self


class TemplateVersionCreateRequest(BaseModel):
    paper_size: PaperSize
    content: TemplateContent
    change_note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _custom_size(self):
        _check_custom_size(self.paper_size, self.content)
        return self


class TemplateUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
