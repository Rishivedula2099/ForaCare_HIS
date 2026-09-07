# ForaCare HIS – User Acceptance Testing (UAT) Scenarios
**Document Reference:** `docs/uat-scenarios.md`  
**Status:** ACTIVE  
**Lifecycle Stage:** Phase 0 – Requirements & Readiness  

---

## 1. Stakeholders, UAT Users & Production Ownership

| Role in UAT | Name / Identifier | Contact / Details | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Production Owner** | TBD (Client Project Sponsor) | TBD | Final business sign-off and production go-live authorization. |
| **UAT Lead / Coordinator** | Dev 1 & Dev 2 | Lead Engineers | Test environment setup, test data staging, defect tracking. |
| **Receptionist Tester** | `uat_receptionist` | Reception Desk Lead (TBD) | Patient registration, search, token generation, billing collection. |
| **Doctor Tester (OPD)** | `uat_doctor_opd` | Medical Officer (TBD) | Queue navigation, vitals review, clinical consultation, e-prescribing. |
| **Doctor Tester (IPD)** | `uat_doctor_ipd` | Senior Resident / Physician (TBD) | Inpatient rounds, admission order, discharge summary creation. |
| **Nurse Tester** | `uat_nurse` | Nursing Supervisor (TBD) | Vitals logging, bed transfers, patient wristband verification. |
| **Lab Technician Tester** | `uat_lab_tech` | Senior Lab Technician (TBD) | Barcode scanning, sample collection, test result entry. |
| **Lab Approver Tester** | `uat_pathologist` | Consultant Pathologist (TBD) | Result clinical verification, amendment, final authorization. |
| **Hospital Administrator** | `uat_admin` | Operations Manager (TBD) | Master data configuration, user provisioning, audit review. |

---

## 2. End-to-End UAT Scenario Register

### Scenario UAT-01: OPD Walk-in Registration, Queue Management, Consultation & Prescription
* **Module:** Patient Registration $\rightarrow$ OPD $\rightarrow$ Consultation $\rightarrow$ Documents
* **Target Role:** Receptionist (`uat_receptionist`), Doctor (`uat_doctor_opd`)
* **Prerequisites:** Doctor schedule active; OPD consultation service tariff active in billing master.
* **Test Steps:**
  1. Receptionist opens Patient Registration, inputs new patient demographics (Name, DOB, Mobile, Gender, Address).
  2. Submits registration $\rightarrow$ System generates unique Patient UID (e.g. `FC01-202609-000101`).
  3. Receptionist books OPD Walk-in consultation for Cardiology under Dr. Sharma.
  4. System prompts for consultation fee payment (₹500); receptionist records Cash payment and clicks Print Token.
  5. 80mm thermal slip prints with Token No. (e.g., `CAR-014`) and verification QR code.
  6. Doctor logs into OPD Console; sees Patient in WAITING queue with Token `CAR-014`.
  7. Doctor clicks "Call Patient" (Status changes to `IN_CONSULTATION`).
  8. Doctor enters vitals (BP: 120/80, Pulse: 74, Temp: 98.4°F), diagnosis "Essential Hypertension", prescribes Amlodipine 5mg OD x 30 days.
  9. Doctor clicks "Complete Consultation" and prints official Prescription Slip.
* **Expected Outcome:** Patient status moves to `COMPLETED`; prescription PDF displays with hospital header, QR code, and doctor signature block; billing reflects collected ₹500 in Cashier shift total.
* **Pass / Fail Criteria:** All steps executed without error; printed slip formatted cleanly on 80mm and A4.
* **Status:** READY

---

### Scenario UAT-02: Laboratory Order Requisition, Accession, Barcode, Result Entry & Pathologist Sign-off
* **Module:** OPD Consultation $\rightarrow$ Billing $\rightarrow$ Laboratory $\rightarrow$ Reporting
* **Target Role:** Doctor, Cashier, Lab Tech (`uat_lab_tech`), Pathologist (`uat_pathologist`)
* **Prerequisites:** Lab tests "Complete Blood Count (CBC)" and "Lipid Profile" configured in Test Master with parameter reference ranges.
* **Test Steps:**
  1. Doctor adds CBC and Lipid Profile to patient consultation order.
  2. Patient visits Lab Reception / Cashier; cashier reviews pending lab requisition, collects payment, and confirms order.
  3. Order appears in Lab Accession Queue.
  4. Lab Technician clicks "Accession & Print Barcode". System issues Accession ID `LAB-260907-0050` and prints 50x25mm vial barcode labels.
  5. Technician collects EDTA blood and Serum samples, scans the physical barcode via USB scanner to confirm collection.
  6. Technician enters test parameter values (e.g., Hemoglobin: 8.2 g/dL [LOW flag triggered], Total Cholesterol: 240 mg/dL [HIGH flag triggered]).
  7. Technician submits results for approval (Status: `PENDING_APPROVAL`).
  8. Pathologist opens Verification Queue, reviews abnormal flags, adds clinical interpretation comment ("Mild microcytic hypochromic anemia"), and clicks "Electronically Sign & Approve".
* **Expected Outcome:** Final status is `APPROVED`. PDF report generated with NABL header, critical flags highlighted in red/amber, pathologist digital signature block, and anti-tamper verification QR.
* **Pass / Fail Criteria:** Abnormal values correctly flagged; PDF report adheres strictly to `TPL-LAB-RPT` specification.
* **Status:** READY

---

### Scenario UAT-03: IPD Admission, Bed Allocation, Transfer, Daily Care, and Discharge Settlement
* **Module:** IPD $\rightarrow$ Bed Master $\rightarrow$ Billing $\rightarrow$ Clinical Discharge
* **Target Role:** Receptionist / Admission Desk, Nurse (`uat_nurse`), Doctor (`uat_doctor_ipd`), Cashier
* **Prerequisites:** General Ward (Bed G-101) and ICU (Bed ICU-02) available in Bed Master.
* **Test Steps:**
  1. Doctor recommends IPD admission from OPD.
  2. Admission Desk selects Patient, assigns Bed G-101 (General Ward).
  3. System enforces mandatory initial admission deposit of ₹5,000. Cashier records payment and prints Deposit Receipt.
  4. Admission Face Sheet and Patient Wristband print. Bed G-101 state changes to `OCCUPIED`.
  5. Nurse admits patient to ward, attaches wristband, records baseline vitals.
  6. Day 2: Patient condition deteriorates; nurse initiates bed transfer to ICU Bed ICU-02. Bed G-101 becomes `CLEANING_IN_PROGRESS` and then `AVAILABLE`. ICU-02 becomes `OCCUPIED`.
  7. Day 4: Doctor creates Clinical Discharge Summary, inputs hospital course, discharge medications, and signs off.
  8. Cashier generates Final IPD Bill: aggregates 1 day General Ward (₹1,500), 2 days ICU (₹10,000), nursing fees (₹2,000), and lab tests (₹1,500) = Total ₹15,000.
  9. System deducts ₹5,000 initial deposit; balance due is ₹10,000. Patient pays balance; cashier marks invoice settled.
  10. Discharge cleared in system; ICU Bed ICU-02 transitions to `CLEANING_IN_PROGRESS`.
* **Expected Outcome:** Complete financial audit trail maintained; no bed can be double-booked; discharge summary printed cleanly.
* **Pass / Fail Criteria:** Bed state machine transitions accurately; deposit correctly adjusted in final invoice; bed freed upon settlement.
* **Status:** READY

---

### Scenario UAT-04: Role-Based Access Control (RBAC) & Multi-Hospital Tenancy Isolation
* **Module:** Auth $\rightarrow$ Core Security $\rightarrow$ Audit
* **Target Role:** Receptionist, Doctor, Auditor (`uat_admin`)
* **Prerequisites:** Two hospital facilities configured: Facility A (`FC-01`) and Facility B (`FC-02`).
* **Test Steps:**
  1. Receptionist logs in with valid credentials; attempts to access `/api/v1/administration/tenants` $\rightarrow$ System returns `403 Forbidden`.
  2. Receptionist attempts to access Doctor's clinical prescription modification endpoint directly $\rightarrow$ Returns `403 Forbidden`.
  3. Doctor logs into Facility A; attempts to view patient records belonging exclusively to Facility B $\rightarrow$ System returns `404 Not Found` or `403 Forbidden` due to tenant/facility scope filtering.
  4. User enters 5 incorrect passwords sequentially $\rightarrow$ Account lockout / rate limiting kicks in.
  5. Auditor logs in, navigates to Audit Trail Console; verifies that all patient record views, edits, and failed authorization attempts were recorded with user ID, client IP, timestamp, and facility ID.
* **Expected Outcome:** Strict least-privilege access enforced; tenant boundaries impermeable.
* **Pass / Fail Criteria:** Zero unauthorized data leakage between facilities or across distinct user roles.
* **Status:** READY

---

### Scenario UAT-05: Local Windows Deployment, Docker Orchestration & Batch Controls
* **Module:** Infrastructure $\rightarrow$ Local Deployment $\rightarrow$ Scripts
* **Target Role:** Hospital IT Administrator / Dev 1
* **Prerequisites:** Windows 10/11 64-bit with Docker Desktop installed.
* **Test Steps:**
  1. User clones/unpacks repository onto local Windows drive (`C:\ForaCare_HIS`).
  2. Double-clicks `START_HIS.bat`.
  3. Batch script checks environment, verifies Docker daemon, boots PostgreSQL and backend/frontend containers.
  4. Double-clicks `HEALTHCHECK_HIS.bat` $\rightarrow$ Validates database connection, API endpoint `/health`, and frontend accessibility at `http://localhost:3000`.
  5. User performs test transaction, then runs `BACKUP_HIS.bat`.
  6. Script creates timestamped, compressed SQL dump in `backups/` directory.
  7. User runs `STOP_HIS.bat` $\rightarrow$ Graceful shutdown of all containers.
* **Expected Outcome:** System starts, operates, backs up, and stops cleanly via native Windows batch files without manual command-line typing.
* **Pass / Fail Criteria:** All batch scripts execute cleanly with color-coded success/failure feedback in Windows terminal.
* **Status:** READY

---

### Scenario UAT-06: ABHA Linking (Mock / Sandbox) & Health Record Linkage
* **Module:** Patient 360 $\rightarrow$ ABDM Integration Adapter
* **Target Role:** Receptionist / Patient Coordinator
* **Prerequisites:** Mock ABDM Adapter active in environment configuration (`ABDM_ADAPTER_MODE=MOCK`).
* **Test Steps:**
  1. Receptionist opens existing Patient 360 profile.
  2. Clicks "Link ABHA Address"; inputs mock ABHA address `patient@abdm`.
  3. Clicks "Request OTP"; system prompts for 6-digit OTP (Mock OTP: `123456`).
  4. Enters OTP and submits.
  5. Mock adapter responds with ABHA Profile (ABHA Number, Verification Status `VERIFIED`).
  6. Patient profile in HIS now displays verified ABHA badge and links upcoming OPD/Lab visits as care contexts.
* **Expected Outcome:** ABHA successfully associated with internal patient UID without overwriting internal database keys.
* **Pass / Fail Criteria:** Mock adapter provides zero-latency verification; DB stores ABHA number and linkage metadata cleanly.
* **Status:** READY

---

## 3. UAT Execution Sign-off Matrix

| Scenario Code | Scenario Name | Primary Tester | Test Date | Result (PASS / FAIL) | Defects Logged | Sign-off Signature |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| `UAT-01` | OPD Walk-in, Queue & Consultation | Receptionist & Doctor | TBD | TBD | None | Pending |
| `UAT-02` | Lab Requisition to Pathologist Sign-off | Lab Tech & Pathologist | TBD | TBD | None | Pending |
| `UAT-03` | IPD Admission to Discharge Settlement | Nurse & Cashier | TBD | TBD | None | Pending |
| `UAT-04` | RBAC & Tenancy Isolation | Admin & Auditor | TBD | TBD | None | Pending |
| `UAT-05` | Windows Local Deployment & BAT Scripts | Hospital IT | TBD | TBD | None | Pending |
| `UAT-06` | ABHA Linkage & Care Contexts | Receptionist | TBD | TBD | None | Pending |
