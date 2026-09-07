# ForaCare HIS – Document & Template Register
**Document Reference:** `docs/document-templates.md`  
**Status:** ACTIVE  
**Lifecycle Stage:** Phase 0 – Requirements & Readiness  

---

## 1. Overview & Rendering Standards

Documents and printouts are vital to hospital operations. The system adheres to a dual-engine architecture:
1. **Server-Side Rendered PDFs (Playwright / Headless Chromium):** High-fidelity, archival-grade PDFs rendered from responsive HTML/CSS templates with absolute positioning, vector barcodes, and cryptographic hashes.
2. **Client-Side Direct Print (Browser Print Engine + `@media print` CSS):** Zero-latency direct printing to thermal receipt and slip printers (80mm / 58mm) and laser desktop printers.

---

## 2. Template Register

| Template Code | Template Name | Target Medium | Paper Size | Engine | Dynamic Placeholders | Priority | Owner | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| `TPL-OPD-TOK` | OPD Token Slip | Thermal Printer | 80mm roll | Client CSS / HTML | Hospital Header, Token No, Date/Time, Patient UID, Name, Age/Sex, Dept, Doctor, Room No, Verification QR | P0 | Dev 2 | READY |
| `TPL-OPD-CRD` | Patient Hospital ID Card | Card / Laser | CR80 / A6 | Server Playwright | Patient UID, Barcode (Code 128), Name, DOB/Age, Gender, Blood Group, Emergency Contact, Photo | P1 | Dev 2 | READY |
| `TPL-OPD-RX` | Doctor Prescription Slip | Laser / Desktop | A4 / A5 Portrait | Server / Client | Facility Letterhead, Patient Vitals, Chief Complaints, Diagnosis, Rx Medication Table (Drug, Dosage, Frequency, Duration, Instructions), Lab Orders, Doctor Digital Signature, Follow-up Date | P0 | Dev 2 | READY |
| `TPL-IPD-ADM` | IPD Admission Face Sheet | Laser / Desktop | A4 Portrait | Server Playwright | IPD Admission No, Patient UID, Admitting Doctor, Department, Ward/Room/Bed, Admission Timestamp, Deposit Amount, Emergency Contact, Attending Nurse | P0 | Dev 2 | READY |
| `TPL-IPD-WBD` | IPD Patient Wristband Label | Thermal Barcode | 25mm x 250mm Band | Client / Server | Patient UID, Barcode (Code 128), IPD No, Name, Age/Gender, Admitting Date, Blood Group, Allergies Flag | P0 | Dev 2 | READY |
| `TPL-IPD-CNS` | IPD General & Surgery Consent | Laser / Desktop | A4 Portrait | Server Playwright | Hospital Header, Patient / Legal Guardian Declaration, Proposed Procedure/Surgery Name, Risks Explained, Doctor & Witness Signature Lines | P0 | Dev 2 | READY |
| `TPL-BIL-INV` | Detailed Tax Invoice (OPD/IPD) | Laser / Desktop | A4 Portrait | Server Playwright | Facility GSTIN/Reg No, Invoice No, Date, Patient Info, Itemized Billable Items (Tariff Code, Description, Qty, Unit Rate, Discount, Tax, Net Amount), Total Amount, Balance Due | P0 | Dev 2 | READY |
| `TPL-BIL-RCP` | Payment & Deposit Receipt | Thermal / Laser | 80mm or A5 | Client CSS / HTML | Receipt No, Date/Time, Patient UID, Invoice Ref, Payment Mode (Cash, UPI, Card), Amount Received in Words & Digits, Cashier Name, Signature Line | P0 | Dev 2 | READY |
| `TPL-LAB-BAR` | Lab Sample Tube Label | Thermal Barcode Roll | 50mm x 25mm | Client / Server | Accession Barcode (Code 128), Accession ID, Patient Name (Abbreviated), Age/Sex, Specimen Type (e.g. EDTA, Serum), Test Codes, Collection Timestamp | P0 | Dev 2 | READY |
| `TPL-LAB-RPT` | Laboratory Investigation Report | Laser / Desktop | A4 Portrait | Server Playwright | NABL/Facility Header, Patient Demographics, Referring Doctor, Sample Collection & Verification Timestamps, Parameter Results Table (Parameter, Value, Unit, Reference Range, Flag: Normal/Low/High/Critical), Method/Notes, Pathologist Digital Signature Block, Verification QR | P0 | Dev 2 | READY |
| `TPL-IPD-DSC` | Clinical Discharge Summary | Laser / Desktop | A4 Portrait | Server Playwright | Admission & Discharge Dates, Attending Consultant, Final Diagnosis, History & Physical Findings, In-Hospital Course, Procedures Performed, Condition at Discharge, Discharge Medications, Dietary Advice, Emergency Warning Signs, Follow-up Appointment | P0 | Dev 2 | READY |
| `TPL-BIL-SFT` | Cashier Shift Closing Report | Thermal / Laser | 80mm or A4 | Client CSS / HTML | Shift Start/End, Cashier Name, Total Invoices, Breakdown by Mode (Cash, UPI, Card), Refunds Issued, Net Cash Handover, Audit Checklist | P1 | Dev 1 & Dev 2 | READY |

---

## 3. Template Technical Specifications

### 3.1. Verification QR Code Standard
Templates carrying verification QR codes (`TPL-OPD-TOK`, `TPL-LAB-RPT`, `TPL-BIL-INV`, `TPL-IPD-DSC`) encode a signed URL:
`https://<HIS_DOMAIN>/verify/doc?t=<DOC_TYPE>&id=<DOC_UUID>&sig=<HMAC_SHA256>`
Scanning the QR in a mobile browser validates authenticity against the HIS backend without exposing private health data publicly.

### 3.2. Barcode Standards
- **Standard:** Code 128 (high density alphanumeric) or 2D DataMatrix.
- **Accession Barcode Data:** `<ACCESSION_ID>` (e.g., `ACC260907-0042`).
- **Patient Wristband Barcode Data:** `<PATIENT_UID>` (e.g., `FC01-202609-000102`).

### 3.3. Standard Styling Rules (`@media print`)
```css
@page {
  size: A4 portrait;
  margin: 12mm 15mm 15mm 15mm;
}

@page thermal {
  size: 80mm auto;
  margin: 0;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #0f172a;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
```

### 3.4. Template Versioning & Extensibility
All template definitions are registered in `DocumentTemplate` database table with:
- `template_code` (e.g., `TPL-LAB-RPT`)
- `version` (e.g., `1.0.0`)
- `header_html` (Facility-customizable header/letterhead)
- `body_html` (Jinja2 / React SSR template body)
- `footer_html` (Disclaimers, signatures, pagination)
- `is_active` (boolean)
