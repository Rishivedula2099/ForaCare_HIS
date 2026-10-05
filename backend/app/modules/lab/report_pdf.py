"""P6-B08: renders a `LabReportOut` into an actual PDF document.

`fpdf2` builds the document natively (header/table/signature block, plus its
built-in Code 39 barcode primitive for the accession barcode); `qrcode`
renders the verification QR as an image fpdf2 embeds, since fpdf2 has no
native QR support. Both are a deliberately lightweight, pure-Python choice
over a headless-browser render (`docs/document-templates.md`'s "Server
Playwright" engine note) - no system/browser dependency, no cross-service
call to the frontend to fetch an authenticated page.
"""
import io

import qrcode
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app.modules.lab.schemas import LabReportOut

_CRITICAL_RED = (178, 24, 43)
_HEADER_GRAY = (71, 85, 105)
_BORDER_GRAY = (203, 213, 225)
_MUTED_GRAY = (100, 116, 139)


def _flag_color(flag: str) -> tuple[int, int, int]:
    if flag == "CRITICAL":
        return _CRITICAL_RED
    if flag in ("HIGH", "LOW"):
        return (180, 120, 10)
    if flag == "NORMAL":
        return (5, 122, 85)
    return _MUTED_GRAY


def _reference_range_label(row) -> str:
    if row.normal_min is None or row.normal_max is None:
        return "-"
    return f"{row.normal_min} - {row.normal_max}"


def build_lab_report_pdf(report: LabReportOut, *, verify_url: str | None) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margin(15)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- Letterhead -----------------------------------------------------
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 8, text=report.facility_name, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_HEADER_GRAY)
    pdf.cell(0, 6, text="Laboratory Investigation Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, text=report.facility_code, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(*_HEADER_GRAY)
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, pdf.get_y() + 2, pdf.w - pdf.r_margin, pdf.get_y() + 2)
    pdf.ln(6)

    # --- Patient / order grid --------------------------------------------
    pdf.set_font("Helvetica", "", 9)
    col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / 2

    def field(label: str, value: str) -> None:
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*_MUTED_GRAY)
        pdf.cell(col_w, 4, text=label, new_x=XPos.LEFT, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(col_w, 5, text=value, new_x=XPos.LEFT, new_y=YPos.NEXT)

    rows_of_fields = [
        ("Patient", report.patient_name, "UID / MRN", f"{report.patient_uid} / {report.patient_mrn}"),
        (
            "Age / Gender",
            f"{report.patient_age_years}y / {report.patient_gender}",
            "Referring Doctor",
            report.referring_doctor_name or "-",
        ),
        (
            "Order Number",
            report.order_number,
            "Accession Number",
            report.accession_number or "-",
        ),
        ("Test", report.test_name, "Collected", _fmt(report.collected_at)),
    ]
    for left_label, left_value, right_label, right_value in rows_of_fields:
        start_y = pdf.get_y()
        field(left_label, left_value)
        pdf.set_xy(pdf.l_margin + col_w, start_y)
        field(right_label, right_value)
        pdf.ln(1)

    pdf.ln(2)

    # --- Critical banner --------------------------------------------------
    has_critical = any(row.flag == "CRITICAL" for row in report.rows)
    if has_critical:
        pdf.set_fill_color(252, 226, 226)
        pdf.set_text_color(*_CRITICAL_RED)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(
            0, 7, text="  This report contains one or more CRITICAL values.",
            fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

    # --- Result table -------------------------------------------------
    headers = ["Parameter", "Value", "Unit", "Reference Range", "Flag"]
    widths = [55, 28, 22, 40, 25]
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_draw_color(*_HEADER_GRAY)
    pdf.set_line_width(0.3)
    for header, width in zip(headers, widths):
        pdf.cell(width, 6, text=header, border="B", new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.ln(7)

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_draw_color(*_BORDER_GRAY)
    for row in report.rows:
        name = f"{row.parameter_name} ({row.parameter_code})"
        if row.is_amended:
            name += " *"
        pdf.cell(widths[0], 6, text=name, border="B", new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(widths[1], 6, text=row.value, border="B", new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.cell(widths[2], 6, text=row.unit or "-", border="B", new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(widths[3], 6, text=_reference_range_label(row), border="B", new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_text_color(*_flag_color(row.flag))
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(widths[4], 6, text=row.flag, border="B", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 8.5)

    if any(row.is_amended for row in report.rows):
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(*_MUTED_GRAY)
        pdf.cell(0, 5, text="* amended since first entered - see revision history", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)

    pdf.ln(6)

    # --- Verification block (QR + accession barcode) ----------------------
    block_top = pdf.get_y()
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*_MUTED_GRAY)
    pdf.cell(0, 5, text=f"Verified by: {report.verified_by_name or '-'}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(
        0, 5,
        text=f"({_fmt(report.verified_at)})" if report.verified_at else "",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.cell(0, 5, text=f"Approved by: {report.approved_by_name or '-'}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(
        0, 5,
        text=f"({_fmt(report.approved_at)})" if report.approved_at else "",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    if report.report_checksum:
        pdf.set_font("Helvetica", "", 6.5)
        pdf.cell(0, 4, text=f"Checksum: {report.report_checksum[:32]}...", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)

    if verify_url:
        qr_img = qrcode.make(verify_url)
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        qr_size = 24
        pdf.image(qr_buffer, x=pdf.w - pdf.r_margin - qr_size, y=block_top, w=qr_size, h=qr_size)
        pdf.set_font("Helvetica", "", 6)
        pdf.set_xy(pdf.w - pdf.r_margin - qr_size, block_top + qr_size)
        pdf.cell(qr_size, 4, text="Scan to verify", align="C")

    if report.accession_number:
        pdf.set_y(max(pdf.get_y(), block_top + 30))
        pdf.set_font("Helvetica", "", 7)
        pdf.cell(0, 4, text=report.accession_number, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.code39(report.accession_number, x=pdf.l_margin, y=pdf.get_y(), w=0.8, h=10)
        pdf.ln(14)

    # --- Signature block --------------------------------------------------
    pdf.set_y(max(pdf.get_y() + 8, pdf.h - 40))
    sig_y = pdf.get_y()
    pdf.set_draw_color(*_HEADER_GRAY)
    pdf.line(pdf.l_margin, sig_y, pdf.l_margin + 70, sig_y)
    pdf.line(pdf.w - pdf.r_margin - 70, sig_y, pdf.w - pdf.r_margin, sig_y)
    pdf.set_xy(pdf.l_margin, sig_y + 1)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.cell(70, 5, text=f"Pathologist Signature ({report.approved_by_name or '-'})")
    pdf.set_xy(pdf.w - pdf.r_margin - 70, sig_y + 1)
    pdf.cell(70, 5, text="Lab Stamp")

    # Auto page break would otherwise trigger a blank second page here -
    # `pdf.h - 12` sits past the 15mm break margin set at the top.
    pdf.set_auto_page_break(auto=False)
    pdf.set_y(pdf.h - 12)
    pdf.set_font("Helvetica", "I", 6.5)
    pdf.set_text_color(*_MUTED_GRAY)
    pdf.cell(0, 4, text=f"Generated {_fmt(report.generated_at)} - {report.order_number}", align="C")

    output = pdf.output()
    return bytes(output)


def _fmt(value) -> str:
    if value is None:
        return "-"
    return value.strftime("%d-%b-%Y %H:%M")
