"""P7-B04: paper formats and layout settings shared by the HTML templates and
the PDF renderer.

A format is either a fixed page (A4/A5/A6, custom labels) or a continuous
thermal roll with a fixed width whose height follows the content.
"""
from dataclasses import dataclass

from app.core.exceptions import AppError

CUSTOM = "CUSTOM"
CUSTOM_MIN_MM = 20
CUSTOM_MAX_MM = 300


@dataclass(frozen=True)
class PageSpec:
    """A fully resolved page: what the template CSS and the renderer need."""

    width_mm: float
    height_mm: float | None  # None = continuous roll, sized to the content
    margin_mm: float
    font_pt: float
    columns: int
    # Small formats (thermal, labels): no signature lines, no page footer.
    compact: bool

    @property
    def paged(self) -> bool:
        """Whether a "Page X of Y" footer makes sense (office paper only)."""
        return not self.compact


@dataclass(frozen=True)
class PaperFormat:
    label: str
    page: PageSpec


PAPER_FORMATS: dict[str, PaperFormat] = {
    "A4": PaperFormat("A4", PageSpec(210, 297, 15, 10, 2, False)),
    "A5": PaperFormat("A5", PageSpec(148, 210, 12, 9.5, 2, False)),
    "A6": PaperFormat("A6", PageSpec(105, 148, 8, 8.5, 1, False)),
    "THERMAL_58": PaperFormat("Thermal 58mm", PageSpec(58, None, 2, 8, 1, True)),
    "THERMAL_80": PaperFormat("Thermal 80mm", PageSpec(80, None, 3, 9, 1, True)),
}
PAPER_SIZES = (*PAPER_FORMATS, CUSTOM)
PAPER_SIZE_LABELS = {code: fmt.label for code, fmt in PAPER_FORMATS.items()} | {CUSTOM: "Custom label"}


@dataclass
class RenderSettings:
    """Layout choices a document template version (or the caller) can make."""

    paper_size: str = "A4"
    header_note: str | None = None
    footer_text: str | None = None
    show_facility_contact: bool = True
    signature_labels: list[str] | None = None
    # Only used when paper_size == CUSTOM (e.g. a 50x25mm specimen label).
    custom_width_mm: float | None = None
    custom_height_mm: float | None = None

    def page(self) -> PageSpec:
        if self.paper_size == CUSTOM:
            width, height = self.custom_width_mm, self.custom_height_mm
            if width is None or height is None:
                raise AppError("A custom paper size needs width_mm and height_mm.", code="INVALID_PAPER_SIZE")
            if not (CUSTOM_MIN_MM <= width <= CUSTOM_MAX_MM and CUSTOM_MIN_MM <= height <= CUSTOM_MAX_MM):
                raise AppError(
                    f"Custom dimensions must be {CUSTOM_MIN_MM}-{CUSTOM_MAX_MM} mm.", code="INVALID_PAPER_SIZE"
                )
            return PageSpec(width, height, 2, 7, 1, True)
        paper = PAPER_FORMATS.get(self.paper_size)
        if paper is None:
            raise AppError(f"Unknown paper size '{self.paper_size}'.", code="INVALID_PAPER_SIZE")
        return paper.page
