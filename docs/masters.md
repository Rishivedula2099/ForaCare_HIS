# ForaCare HIS – Master Data Register
**Document Reference:** `docs/masters.md`  
**Status:** ACTIVE  
**Lifecycle Stage:** Phase 0 – Requirements & Readiness  

---

## 1. Overview & Master Data Architecture

Master data defines the operational foundation for ForaCare HIS. All masters adhere to the following principles:
- **Tenancy Boundary:** Configured per `tenant_id` and optionally scoped per `facility_id`.
- **Soft Deletion & Auditability:** Masters are never hard-deleted once referenced by operational records (`is_active: bool`).
- **Seed Strategy:** Core system masters (Roles, Default Payment Methods, Standard Document Templates) are seeded automatically via Alembic migrations. Hospital-specific masters (Doctors, Departments, Tariff Catalogs, Lab Tests) are imported via standard CSV seeds or managed via the Admin Console.

---

## 2. Master Data Register

| Master ID | Master Entity Name | Scope | Seeding Method | Mandatory Fields | Status | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `MST-TEN-01` | **Tenant / Organization Master** | Global | Migration Seed | `id`, `name`, `slug`, `code`, `is_active`, `created_at` | READY | Dev 1 |
| `MST-FAC-01` | **Facility / Hospital Branch Master** | Tenant | Migration / Admin UI | `id`, `tenant_id`, `name`, `facility_code`, `address`, `phone`, `email`, `timezone`, `currency`, `letterhead_config` | READY | Dev 1 |
| `MST-DEP-01` | **Department Master** | Facility | CSV / Admin UI | `id`, `facility_id`, `name`, `code` (e.g. `CARD`, `ORTH`), `type` (`CLINICAL`, `DIAGNOSTIC`, `ADMINISTRATIVE`), `is_active` | READY | Dev 1 |
| `MST-DOC-01` | **Doctor / Practitioner Master** | Facility | CSV / Admin UI | `id`, `facility_id`, `user_id`, `name`, `reg_number`, `specialization`, `department_id`, `opd_fee`, `opd_followup_fee`, `room_number`, `is_active` | READY | Dev 1 |
| `MST-USR-01` | **User & Role Master** | Tenant | Migration / Admin UI | `id`, `tenant_id`, `facility_id`, `username`, `email`, `password_hash`, `full_name`, `role` (`SUPER_ADMIN`, `HOSPITAL_ADMIN`, `DOCTOR`, `RECEPTIONIST`, `NURSE`, `LAB_TECH`, `LAB_APPROVER`), `is_active` | READY | Dev 1 |
| `MST-WRD-01` | **Ward Master** | Facility | CSV / Admin UI | `id`, `facility_id`, `department_id`, `name`, `code`, `gender_restriction` (`MALE`, `FEMALE`, `ALL`), `floor_number`, `is_active` | READY | Dev 1 |
| `MST-ROM-01` | **Room Master** | Facility | CSV / Admin UI | `id`, `facility_id`, `ward_id`, `room_number`, `room_type` (`GENERAL`, `SEMI_PRIVATE`, `PRIVATE`, `DELUXE`, `ICU`), `is_active` | READY | Dev 1 |
| `MST-BED-01` | **Bed Master** | Facility | CSV / Admin UI | `id`, `facility_id`, `ward_id`, `room_id`, `bed_number`, `bed_type`, `daily_charge`, `status` (`AVAILABLE`, `OCCUPIED`, `CLEANING_IN_PROGRESS`, `MAINTENANCE`), `is_active` | READY | Dev 1 |
| `MST-SRV-01` | **Service / Tariff Master** | Facility | CSV / Admin UI | `id`, `facility_id`, `category` (`CONSULTATION`, `PROCEDURE`, `BED_CHARGE`, `NURSING`, `DIAGNOSTIC`), `code`, `name`, `unit_rate`, `tax_percentage`, `is_active` | READY | Dev 1 |
| `MST-LAB-01` | **Lab Test Master** | Facility | CSV / Admin UI | `id`, `facility_id`, `department_id`, `test_code` (e.g. `CBC`, `LIPID`), `name`, `specimen_type` (`EDTA_BLOOD`, `SERUM`, `URINE`), `container_type` (`LAVENDER_TOP`, `RED_TOP`), `tat_minutes`, `unit_price`, `is_active` | READY | Dev 1 |
| `MST-PAR-01` | **Lab Parameter & Reference Range Master** | Global / Facility | CSV / Admin UI | `id`, `test_id`, `parameter_code`, `name`, `unit` (e.g. `g/dL`, `mg/dL`), `gender` (`ALL`, `MALE`, `FEMALE`), `age_min_days`, `age_max_days`, `normal_min`, `normal_max`, `critical_low`, `critical_high`, `sequence_order` | READY | Dev 1 |
| `MST-PAY-01` | **Payment Method Master** | Global / Facility | Migration Seed | `id`, `code` (`CASH`, `UPI_QR`, `CREDIT_CARD`, `DEBIT_CARD`, `BANK_TRANSFER`, `CHEQUE`), `name`, `requires_ref_number`, `is_active` | READY | Dev 1 |
| `MST-TPL-01` | **Document Template Master** | Tenant / Facility | Migration Seed | `id`, `template_code` (`TPL-OPD-TOK`, `TPL-LAB-RPT`, etc.), `name`, `version`, `paper_size`, `header_html`, `body_html`, `footer_html`, `is_active` | READY | Dev 1 & Dev 2 |

---

## 3. Mandatory Seed Data Specifications

### 3.1. Standard Clinical Departments
1. **General Medicine** (`GENMED`)
2. **Pediatrics** (`PED`)
3. **Obstetrics & Gynecology** (`OBGYN`)
4. **General Surgery** (`GENSUR`)
5. **Orthopedics** (`ORTHO`)
6. **Cardiology** (`CARDIO`)
7. **Dermatology** (`DERMA`)
8. **Pathology / Diagnostic Laboratory** (`PATH`)
9. **Emergency & Trauma** (`EMERG`)

### 3.2. Initial Lab Test Master Catalog (Baseline Seeds)
| Test Code | Test Name | Specimen | Sample Container | TAT | Default Rate |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `CBC` | Complete Blood Count (14 Parameters) | Whole Blood | Lavender Top (EDTA) | 60 min | ₹350 |
| `LIPID` | Lipid Profile (Cholesterol, HDL, LDL, Triglycerides) | Serum | Red Top (Clot Activator) | 120 min | ₹650 |
| `LFT` | Liver Function Test (Bilirubin, SGOT, SGPT, Alk Phos) | Serum | Red Top (Clot Activator) | 120 min | ₹600 |
| `KFT` | Kidney Function Test (Urea, BUN, Creatinine, Uric Acid) | Serum | Red Top (Clot Activator) | 120 min | ₹550 |
| `FBS` | Fasting Blood Sugar | Plasma | Gray Top (Sodium Fluoride) | 30 min | ₹100 |
| `PPBS` | Post-Prandial Blood Sugar | Plasma | Gray Top (Sodium Fluoride) | 30 min | ₹100 |
| `URINE-RE` | Urine Routine & Microscopic Examination | Urine | Sterile Container | 45 min | ₹150 |
| `WIDAL` | Widal Test for Typhoid | Serum | Red Top (Clot Activator) | 60 min | ₹250 |

### 3.3. Baseline Parameter & Reference Range Seeds for CBC (Sample)
| Parameter Code | Name | Unit | Gender | Normal Min | Normal Max | Critical Low | Critical High |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `HB_M` | Hemoglobin (Male) | g/dL | MALE | 13.0 | 17.5 | 7.0 | 20.0 |
| `HB_F` | Hemoglobin (Female) | g/dL | FEMALE | 12.0 | 15.5 | 7.0 | 20.0 |
| `TLC` | Total Leukocyte Count (WBC) | cells/mcL | ALL | 4,000 | 11,000 | 2,000 | 30,000 |
| `PLT` | Platelet Count | lakhs/mcL | ALL | 1.5 | 4.5 | 0.5 | 10.0 |
| `RBC_M` | Red Blood Cell Count (Male) | mill/mcL | MALE | 4.5 | 5.9 | 2.5 | 7.0 |
| `RBC_F` | Red Blood Cell Count (Female) | mill/mcL | FEMALE | 4.0 | 5.2 | 2.5 | 6.5 |

---

## 4. Master Import & Migration Policy

1. **Greenfield Bootstrap:**
   - Database migrations will populate base system roles, default payment methods, and initial document templates.
   - Initial facility deployment provides pre-configured CSV templates in `backend/app/seeds/data/` for rapid catalog onboarding.
2. **Validation Rules on Upload:**
   - Uniqueness enforced on `(facility_id, code)` across all masters.
   - All rates and charges must be non-negative decimals ($>= 0.00$).
   - Lab reference ranges must satisfy `critical_low < normal_min < normal_max < critical_high`.
