# ForaCare HIS – Requirements & Business Rules Specification
**Document Reference:** `docs/requirements.md`  
**Status:** FROZEN (Phase 0 Baseline)  
**Lifecycle Stage:** Phase 0 – Requirements & Readiness  

---

## 1. Hospital & Facility Information

| Attribute | Specification | Status | Owner |
| :--- | :--- | :--- | :--- |
| **Primary Organization (Tenant)** | ForaCare Health Group (Multi-tenant schema support) | AVAILABLE | Lead Architect |
| **Initial Facility (Hospital 1)** | TBD (Designated pilot hospital / clinic) | TBD | Production Owner |
| **Facility Code / Identifier** | TBD (e.g., `FC-HOSP-01`) | TBD | Production Owner |
| **Physical Address** | TBD | TBD | Production Owner |
| **Registration / License No.** | State Clinical Establishment Registration No. (TBD) | TBD | Hospital Admin |
| **Contact Info (Phone / Email)** | TBD | TBD | Hospital Admin |
| **Operational Timezone** | Asia/Kolkata (IST, UTC+05:30) | AVAILABLE | Dev 1 |
| **Currency** | Indian Rupee (INR, ₹) | AVAILABLE | Dev 1 |

---

## 2. Product Branding & Identity

| Element | Specification | Status | Owner |
| :--- | :--- | :--- | :--- |
| **Product Name** | ForaCare HIS / HMIS | AVAILABLE | Product Owner |
| **Logo (Digital / App Shell)** | SVG / High-res PNG (Dark & Light mode compatible) | TBD | Dev 2 |
| **Logo (Print Headers)** | Grayscale / Monochrome High-Contrast PNG (Optimized for thermal & laser print) | TBD | Dev 2 |
| **Color Tokens** | Primary: Hospital Deep Slate / Teal (`#0F766E` / `#0E7490`), Neutral: Slate (`#0F172A`), Destructive: Rose (`#E11D48`) | AVAILABLE | Dev 2 |
| **Document Letterhead Standard** | Hospital Name, Address, Contact, Reg No., NABH/NABL accreditation badges (if any) | TBD | Hospital Admin |
| **Document Footer Standard** | "Generated via ForaCare HIS", Verification QR Code, Page N of M, Signature Block | AVAILABLE | Dev 1 & Dev 2 |

---

## 3. User Roles & Permission Matrix

The system enforces Role-Based Access Control (RBAC) across all modules with tenant/facility tenancy enforcement.

| Role Code | Role Name | Description & Key Responsibilities |
| :--- | :--- | :--- |
| `SUPER_ADMIN` | Global Platform Admin | Multi-tenant setup, facility provisioning, system diagnostics, global configs. |
| `HOSPITAL_ADMIN` | Hospital / Facility Admin | User management, doctor/department master setup, tariff/service configuration. |
| `RECEPTIONIST` | Front Desk / Cashier | Patient registration, search, OPD booking, token issue, invoice creation, billing collections, receipt printing. |
| `DOCTOR` | OPD / IPD Physician | View OPD queue, record vitals, clinical consultation, e-prescriptions, lab order requisition, IPD admission notes, discharge summary. |
| `NURSE` | Ward / Triage Nurse | Vitals capture, IPD bed transfer tracking, nursing care notes, sample dispatch. |
| `LAB_TECHNICIAN` | Laboratory Technician | Sample accessioning, barcode generation/scanning, sample collection, test result entry. |
| `LAB_APPROVER` | Pathologist / Lab Director | Review entered lab results, amend/correct values, clinical verification, final electronic approval. |
| `AUDITOR` | Compliance / Auditor | Read-only access to audit trail logs, financial reconciliation reports, patient access history. |

### Permissions Mapping

| Module / Operation | Super Admin | Hospital Admin | Receptionist / Cashier | Doctor | Nurse | Lab Tech | Lab Approver | Auditor |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tenant / Facility Config** | CRUD | R | - | - | - | - | - | R |
| **User & Role Management** | CRUD | CRUD | - | - | - | - | - | R |
| **Patient Registration & 360** | R | CRUD | CRUD | R/Update | R | R | R | R |
| **OPD Queue & Token** | R | Manage | CRUD | Manage Queue | R | - | - | R |
| **Clinical Consultation** | - | - | - | CRUD | R | - | - | R |
| **IPD Bed & Admission** | R | Manage | Admit/Discharge | Admit/Discharge | Manage | - | - | R |
| **Invoicing & Payments** | R | Tariff CRUD | CRUD | View | View | View | View | R |
| **Lab Requisition** | R | - | Create Order | Create Order | - | R | R | R |
| **Lab Sample / Barcode** | - | - | - | - | Update | CRUD | R | R |
| **Lab Result Entry** | - | - | - | - | - | CRUD | CRUD | R |
| **Lab Report Approval** | - | - | - | - | - | - | Approve/Reject | R |
| **Document Template Setup** | CRUD | CRUD | - | - | - | - | - | R |
| **Audit Logs** | R | R | - | - | - | - | - | Full R |

---

## 4. Workflows & Business Rules

### 4.1. Patient Registration & Patient 360
- **Hospital Patient UID Generation:** Formatted as `<FACILITY_CODE>-YYYYMM-<6_DIGIT_SEQ>` (e.g., `FC01-202609-000102`). Unique per tenant.
- **Deduplication Check:** Real-time search by mobile number, Aadhaar/Government ID, and Name + Year of Birth. Prevents duplicate UID creation.
- **Identity Decoupling:** Internal Patient UID is permanent. ABHA Address / ABHA Number is an external link and must never replace the internal primary key.
- **Demographics:** Name, Age/DOB, Gender, Phone, Address, Emergency Contact, Blood Group, Guardian details for minors.

### 4.2. OPD Business Rules
- **Walk-in & Appointment:** Supports both pre-booked time-slot appointments and instant walk-in registrations.
- **Department & Doctor Allocation:** Each OPD registration is assigned to a specific Department and Consulting Doctor.
- **Token / QR Queue:**
  - Token sequence resets daily per doctor/department (e.g., `DOC-CAR-001`, `DOC-CAR-002`).
  - Physical token slip contains patient details, token number, estimated wait room, and a verification QR code.
  - Queue states: `WAITING` $\rightarrow$ `IN_CONSULTATION` $\rightarrow$ `COMPLETED` / `NO_SHOW` / `CANCELLED`.
- **Consultation Output:** Diagnosis (ICD-10 / free text), Chief Complaints, Vitals (BP, Pulse, Temp, SpO2, Weight, Height, BMI), Clinical Advice, Rx Prescriptions, Lab Orders, Follow-up Date.

### 4.3. IPD Business Rules
- **Bed State Machine:** `AVAILABLE` $\rightarrow$ `OCCUPIED` $\rightarrow$ `CLEANING_IN_PROGRESS` $\rightarrow$ `MAINTENANCE` $\rightarrow$ `AVAILABLE`.
- **Admission Criteria:** Requires Patient UID, Admitting Doctor, Diagnosis, Ward/Room/Bed allocation, Emergency Contact, and minimum mandatory admission deposit.
- **Bed Allocation & Transfer:** System logs timestamped transfer events when a patient moves between wards (e.g., General Ward to ICU). Daily bed tariff is calculated accordingly.
- **Admission Documentation:** Automatic generation of Admission Face Sheet, Patient Wristband (with barcode), and Signed Consent Forms.
- **Discharge Gate:** Patient cannot be marked discharged until:
  1. Clinical Discharge Summary is approved by the Attending Physician.
  2. Pharmacy/Lab clearance received (no pending unbilled orders).
  3. Final IPD billing settlement balance is zero (or authorized by admin credit exception).
  4. Bed status automatically switches to `CLEANING_IN_PROGRESS` upon discharge.

### 4.4. Billing & Cashier Rules
- **Tariff & Service Catalog:** Base tariff lists configured per facility with itemized prices for consultations, procedures, bed days, nursing, and lab tests.
- **Dual Flow (OPD vs IPD):**
  - **OPD:** Pay-before-service or instant service billing with immediate receipt generation.
  - **IPD:** Running ledger tracking deposits, intermediate running bills, and final consolidated discharge invoice.
- **Payment Modes:** Cash, UPI / QR, Credit/Debit Card, Bank Transfer, TPA / Insurance (TBD for Phase 2).
- **Receipts & Auditing:**
  - Sequential, non-reusable Receipt Number per financial year.
  - Receipts cannot be deleted. Corrections require audited Credit Notes / Refund Vouchers with mandatory supervisor authorization and reason capture.
  - Cashier Shift Closing report generated at the end of each shift detailing collection by payment mode.

### 4.5. Laboratory Rules
- **Lifecycle Flow:** `ORDER_PLACED` $\rightarrow$ `BILLED` $\rightarrow$ `ACCESSIONED` $\rightarrow$ `SAMPLE_COLLECTED` $\rightarrow$ `IN_TESTING` $\rightarrow$ `RESULT_ENTERED` $\rightarrow$ `VERIFIED_APPROVED` $\rightarrow$ `REPORT_DISPATCHED`.
- **Accession & Barcoding:**
  - Unique Accession ID generated per specimen tube (e.g., `LAB-260907-0042`).
  - Barcode label (Code 128 / QR) printed on 50x25mm roll specifying Accession ID, Patient Name, Age/Gender, Test Name, and Specimen Type (e.g., EDTA Whole Blood, Serum, Urine).
- **Result Entry & Validation:**
  - Auto-flags values outside physiological reference ranges (`LOW`, `NORMAL`, `HIGH`, `CRITICAL`).
  - Critical results trigger visual alerts for emergency doctor notification.
- **Approval & Security:**
  - Only users with `LAB_APPROVER` role can issue final report authorization.
  - Approved reports are sealed into PDF with cryptographic checksum and public verification QR code.
  - Result amendments post-approval require version increment (`v1`, `v2`) with logged audit justification.

### 4.6. Printing Requirements
- **Desktop / Laser (A4 / A5):**
  - IPD Admission Form, Detailed IPD Invoices, Clinical Discharge Summaries, Lab Test Reports, Doctor Prescriptions.
  - Formatted using standard print CSS media queries (`@media print`) and server-side Playwright headless PDF generator.
- **Thermal Printing (80mm / 58mm):**
  - OPD Token Slips, Quick Payment Receipts, Vitals Slips.
  - Monospaced, high-contrast, zero margin layouts.
- **Direct Barcode Labels (50x25mm / 38x25mm):**
  - Patient Wristbands, Lab Sample Collection Tubes.

### 4.7. Data Migration Requirement
- **Scope for Initial Phase:** Greenfield setup.
- **Legacy Migration:** TBD (No legacy database migration required for Phase 1 MVP; bulk import templates for Masters like Doctor list, Tariff catalog, Lab test master will be provided via CSV).

### 4.8. Deployment Requirements
- **Local Deployment:**
  - Target OS: Windows 10 / 11 / Server 2019+
  - Runtimes: Docker Desktop / Docker Engine + Docker Compose
  - Controls: Dedicated Windows `.bat` scripts (`START_HIS.bat`, `STOP_HIS.bat`, `BACKUP_HIS.bat`, `HEALTHCHECK_HIS.bat`, `RESTORE_HIS.bat`)
  - Database: Local PostgreSQL container with persisted volume mapping
- **Cloud Deployment:**
  - Frontend: Vercel / Next.js
  - Backend: Containerized FastAPI on portable Linux container (AWS ECS / Render / Cloud Run)
  - Database: Managed PostgreSQL 15+
  - Object Storage: S3-compatible bucket (Cloudflare R2 / AWS S3)

---

## 5. Requirements Checklist & Traceability

| Req ID | Domain | Requirement Description | P0 / MVP | Status | Owner |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `REQ-SEC-01` | Auth | JWT-based auth with refresh token rotation | P0 | AVAILABLE | Dev 1 |
| `REQ-SEC-02` | RBAC | Role & facility scoped permission checking middleware | P0 | AVAILABLE | Dev 1 |
| `REQ-SEC-03` | Tenancy | Tenant and facility separation on all DB entities | P0 | AVAILABLE | Dev 1 |
| `REQ-PAT-01` | Patient | Patient registration with auto UID generation | P0 | AVAILABLE | Dev 1 & Dev 2 |
| `REQ-PAT-02` | Patient | Deduplication engine on phone & ID | P0 | AVAILABLE | Dev 1 |
| `REQ-PAT-03` | Patient | Patient 360 summary view & timeline | P0 | AVAILABLE | Dev 2 |
| `REQ-OPD-01` | OPD | Walk-in registration & appointment booking | P0 | AVAILABLE | Dev 2 |
| `REQ-OPD-02` | OPD | Daily sequential token generation with verification QR | P0 | AVAILABLE | Dev 1 & Dev 2 |
| `REQ-OPD-03` | OPD | Doctor consultation console (Vitals, Rx, Lab orders) | P0 | AVAILABLE | Dev 2 |
| `REQ-IPD-01` | IPD | Ward, room, bed hierarchy master & real-time state | P0 | AVAILABLE | Dev 1 & Dev 2 |
| `REQ-IPD-02` | IPD | Admission workflow with mandatory deposit | P0 | AVAILABLE | Dev 1 |
| `REQ-IPD-03` | IPD | Bed allocation, transfer history, and release on discharge | P0 | AVAILABLE | Dev 1 |
| `REQ-BIL-01` | Billing | Master tariff management (OPD, IPD, Procedures) | P0 | AVAILABLE | Dev 1 |
| `REQ-BIL-02` | Billing | Invoicing, deposit ledger, payment receipts | P0 | AVAILABLE | Dev 1 & Dev 2 |
| `REQ-BIL-03` | Billing | Cashier shift closing & reconciliation report | P0 | AVAILABLE | Dev 1 |
| `REQ-LAB-01` | Lab | Test master with multi-parameter reference ranges | P0 | AVAILABLE | Dev 1 |
| `REQ-LAB-02` | Lab | Sample accessioning & barcode generation | P0 | AVAILABLE | Dev 1 & Dev 2 |
| `REQ-LAB-03` | Lab | Result entry with auto-flagging of critical values | P0 | AVAILABLE | Dev 2 |
| `REQ-LAB-04` | Lab | Pathologist sign-off & PDF report generation | P0 | AVAILABLE | Dev 1 & Dev 2 |
| `REQ-DOC-01` | Docs | Print engine for 80mm receipts, A4 reports, barcode labels | P0 | AVAILABLE | Dev 2 |
| `REQ-INT-01` | ABHA | ABHA M1/M2/M3 adapter interface with Mock implementation | P0 | AVAILABLE | Dev 1 |
| `REQ-INT-02` | ABHA | ABHA Sandbox / Production live credentials | Phase 2 | TBD | Production Owner |
| `REQ-INT-03` | Payment | Payment Gateway integration (Razorpay / PineLabs) | Phase 2 | TBD | Production Owner |

---

## 6. Blocker & Risk Register

| Blocker ID | Description | Impact | Mitigation / Action | Owner | Target Phase |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `BLK-01` | Official ABDM Sandbox / Production Client ID & Secret unavailable | Cannot test live ABHA verification against NHA servers | Build comprehensive Mock ABHA Adapter matching NHA ABDM API specs for Phase 1 MVP. Live connector plugged in Phase 8. | Dev 1 | Phase 8 |
| `BLK-02` | Pilot hospital physical facility details and letterhead branding missing | Final A4 document print headers cannot be permanently frozen | Provide standard hospital configuration UI with fallback generic branding until pilot assets are supplied. | Dev 2 | Phase 1 |
| `BLK-03` | Payment Gateway Merchant account not yet provisioned | Cannot test automatic payment webhooks | Support manual payment mode recording (`CASH`, `CARD_OFFLINE`, `UPI_QR_MANUAL`) in Phase 1 billing. | Dev 1 | Phase 5 |
| `BLK-04` | Pilot thermal printer hardware model unconfirmed (ESC/POS vs Browser Print) | Direct raw socket thermal printing might vary by hardware | Implement standard web print stylesheets (`@media print`) first, which operate across all Windows-installed thermal drivers. | Dev 2 | Phase 7 |

---

## 7. Sign-off & Ownership

- **Production Owner:** TBD (Pending client appointment)
- **Technical Lead / Dev 1:** Lead Backend & Infra Engineer
- **Frontend Lead / Dev 2:** Lead Frontend & Workflow Engineer
- **UAT Coordinator:** TBD
