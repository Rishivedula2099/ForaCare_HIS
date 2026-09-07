# ForaCare HIS / HMIS Project Context

## 1. Project Objective

ForaCare HIS is a modern hospital information system focused on a desktop/browser-first experience for local Windows deployment, with a future-ready cloud architecture. The initial release prioritizes hospital operations over mobile-first patient experiences.

Primary scope:
- Patient registration and patient 360
- OPD registration and consultation
- Token/QR queue management
- IPD and bed/ward allocation
- Billing and payment workflows
- Laboratory order, collection, results, approval, and reporting
- Documents and printing
- RBAC, audit, multi-hospital tenancy foundation
- ABDM/ABHA integration layer

Non-priority for Phase 1:
- PWA/mobile-first patient apps
- Dedicated patient mobile app
- Advanced AI/RAG workflows
- Radiology, pharmacy, inventory, blood bank, HR, advanced MIS

## 2. Current Direction

The project is designed around a modern multi-hospital HIS/HMIS with the following lifecycle flow:

Patient Registration -> Patient UID / Patient 360 -> OPD -> Token / QR -> Consultation -> IPD -> Ward / Room / Bed -> Billing / Payments -> Laboratory -> Sample / Barcode -> Results / Approval -> Reports / Documents -> ABHA / ABDM

Important strategic principles:
- Keep the backend portable and not tightly coupled to a single cloud platform.
- Support both local hospital deployment and cloud-ready deployment.
- Keep the core product reusable across hospitals without hardcoding a single environment.
- Maintain multi-hospital boundaries and strict facility/tenant separation by default.

## 3. Recommended Technology Stack

### Frontend
- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query
- React Hook Form + Zod

### Backend
- FastAPI
- Python
- Pydantic v2
- SQLAlchemy 2.0
- Alembic
- PostgreSQL
- OpenAPI / Swagger

### Local Deployment
- Docker / Docker Compose
- PostgreSQL
- Optional Redis
- Windows BAT scripts
  - START_HIS.bat
  - STOP_HIS.bat
  - UPDATE_HIS.bat
  - BACKUP_HIS.bat
  - RESTORE_HIS.bat
  - HEALTHCHECK_HIS.bat

### Cloud Deployment
- Vercel for Next.js frontend
- Portable containerized FastAPI backend
- Managed PostgreSQL
- S3-compatible object storage
- Cloudflare where appropriate

### Optional Later
- Redis + ARQ/Celery for jobs
- Sentry/OpenTelemetry observability

## 4. Architecture Summary

The system is composed of:
- Web frontend for hospital users
- Central FastAPI backend containing all hospital modules
- PostgreSQL as the main transactional database
- Object storage for PDFs, documents, and reports
- Integration layer for ABHA/ABDM, payments, and other external systems

High-level flow:

Users -> Browser -> Cloudflare -> Next.js Frontend -> REST / WebSocket -> FastAPI API -> PostgreSQL / Object Storage / Redis (optional) -> Integration Layer -> ABHA / ABDM / Payments / SMS / Email / WhatsApp

### Local Hospital Architecture
- Server / PC in hospital
- START_HIS.bat
- Docker Compose
- Next.js + FastAPI + PostgreSQL
- Local disk / storage backend

### Cloud Architecture
- User
- Cloudflare
- Vercel / Next.js
- FastAPI container
- Managed PostgreSQL
- S3-compatible storage

## 5. Backend Structure Guidance

The backend should follow a modular architecture like this:

backend/
  app/
    main.py
    core/
      config.py
      database.py
      security.py
      permissions.py
      exceptions.py
      middleware.py
    modules/
      auth/
      tenants/
      facilities/
      patients/
      appointments/
      opd/
      queue/
      ipd/
      wards/
      beds/
      billing/
      payments/
      laboratory/
      documents/
      templates/
      reports/
      notifications/
      audit/
      administration/
    integrations/
      abdm/
      payments/
      sms/
      whatsapp/
      email/
      fhir/
    workers/
    shared/
  migrations/
  tests/
  Dockerfile
  docker-compose.yml
  pyproject.toml

API conventions:
- Use /api/v1/... versioned endpoints
- Use generated OpenAPI/Swagger docs
- Keep modules isolated and domain-driven

## 6. Core Modules

### Foundation
- Login
- RBAC
- Tenant/facility setup
- Audit
- Configuration

### Patient
- Patient registration
- Hospital patient UID
- Patient search
- Patient 360
- ABHA linking
- Patient history
- Documents

### OPD
- Registration
- Doctor / department
- Appointment / walk-in
- Token
- QR verification
- Queue
- Consultation
- Prescription

### IPD
- Admission
- Ward / room / bed
- Allocation and transfer
- Deposit
- Consent
- Admission forms / labels
- Discharge
- Bed release

### Billing
- Services / packages
- OPD / IPD invoice
- Deposit
- Payment
- Refund
- Balance
- Receipt

### Laboratory
- Test master
- Parameters / reference ranges
- Lab order
- Accession
- Barcode
- Sample collection
- Result entry
- Verification and approval
- PDF report
- QR verification

### Documents
- Admission label
- Admission form
- Consent
- Token
- Receipt
- Prescription
- Lab report
- Discharge summary
- Hospital-specific templates

### Future Modules
- Radiology
- Pharmacy
- Inventory
- Blood Bank
- Finance
- HR
- MIS

## 7. Multi-Hospital Architecture

The product should support multiple hospitals/organizations as a logical structure:

Hospital A
Hospital B
Hospital C

Every operational record should carry tenant_id and facility_id as relevant.
Cross-hospital access is denied by default.
The hospital patient UID is the internal identifier; ABHA is a linked identity and must not replace the internal patient key.

## 8. Project Lifecycle and Phase Tracker

This project will move in phases. The project definition of done is not merely UI completion; work must include API, database, validation, permissions, audit, error handling, persistence, relevant document/printing, tests, and UAT.

### Phase 0 – Requirements & Readiness
Goals:
- Finalize MVP scope
- Confirm multi-hospital model
- Collect workflows, templates, branding, roles, and masters
- Define integration requirements and UAT owners

### Phase 1 – Technical Foundation
Goals:
- Git repository setup
- Next.js app
- FastAPI app
- PostgreSQL configuration
- SQLAlchemy setup
- Alembic setup
- Docker Compose
- environment files
- UI design system
- application shell/navigation
- authentication, RBAC, tenant/facility context, audit, CI, health checks

Exit gate:
- Login, database, migrations, Docker startup, RBAC, tenant context, and CI all work.

### Phase 2 – Patient Master / Patient 360
Goals:
- Patient DB model
- Patient CRUD APIs
- Registration UI
- Patient UID generation
- Search
- Duplicate checks
- Photo handling
- 360 UI and timeline
- ABHA linkage fields
- Patient access permissions and audit

Exit gate:
- A patient can be created once, assigned a UID, searched, and opened through Patient 360.

### Phase 3 – OPD + Token + QR
Goals:
- Department and doctor masters
- OPD registration
- Appointment/walk-in
- Token generation and queue state handling
- QR generation and verification
- Vitals, consultation, prescription, printing

Exit gate:
- Registration, token, QR, queue, consultation, and prescription work end-to-end.

### Phase 4 – IPD + Bed + Admission
Goals:
- Ward, room, and bed masters
- Bed state machine
- Admission APIs and UI
- Allocation, transfers, deposit linkage, consent, forms, labels, discharge summary, bed release

### Phase 5 – Billing + Payment
Goals:
- Service/package master
- Invoice model and UI
- Deposit, payment recording, refund, balance, receipt, cashier closing
- External payment adapter (later)

### Phase 6 – Laboratory
Goals:
- Lab tests, parameters, reference ranges
- Lab order, accession, barcode
- Sample collection, result entry, verification, approval
- Result amendments/versioning
- Report PDF and QR verification

Exit gate:
- Lab order -> billing -> accession -> barcode -> sample collection -> result -> approval -> report -> print

### Phase 7 – Documents & Printing
Goals:
- Template registry/versioning
- HTML/CSS document templates
- Playwright PDF generation
- Admission forms/labels, consent, receipts, prescriptions, lab reports
- Thermal printing

### Phase 8 – ABHA / ABDM
Goals:
- Adapter interface
- Mock, sandbox, and production implementations
- Authentication and ABHA linking
- Consent workflow
- Production integration only after official access

Important rule:
- Never store production secrets in source code.

### Phase 9 – Security & Hardening
Goals:
- HTTPS
- Auth review
- RBAC tests
- Tenant isolation tests
- Input validation
- Rate limiting
- Secrets management
- Audit review
- QR security
- File access control
- Backup/restore

### Phase 10 – UAT
Focus on end-to-end flows:
- OPD/Lab E2E flow
- IPD E2E flow

UAT tracking should be per module and per scenario.

### Phase 11 – Deployment
- Cloud deployment via GitHub + GitHub Actions + Vercel + FastAPI container + PostgreSQL + object storage
- Local deployment via Docker Compose + Windows BAT scripts

Deployment checklist includes:
- Docker available
- Environment configured
- Database created
- Migrations applied
- Admin user created
- Storage configured
- Backup configured
- Health check passed
- Browser access tested
- Printing tested
- Barcode tested
- QR verification tested

## 9. Team Split

### Developer 1 – Backend / Infrastructure
Owns:
- FastAPI
- PostgreSQL
- SQLAlchemy / Alembic
- Auth / RBAC
- Multi-tenancy
- Patient/IPD/Billing/Lab APIs
- Document APIs
- Integration adapters
- ABHA / ABDM
- Security
- Docker
- Deployment
- Backups

### Developer 2 – Frontend / Workflow
Owns:
- Next.js
- TypeScript
- UI system
- Dashboard
- Patient 360
- OPD
- Token / QR
- IPD
- Billing
- Lab
- Documents
- Printing
- UAT fixes

Both share code review, testing, security, and deployment responsibilities.

## 10. Timeline Guidance

Recommended execution windows:
- Weeks 1–2: Foundation + Patient 360 + OPD + Token/QR + auth/RBAC
- Week 3: IPD + ward/room/bed + admission docs + billing/payment
- Week 4: Lab + sample collection + barcode + result entry + approval + reports
- Week 5: ABDM adapter + document templates + audit/security + integration testing
- Week 6: UAT + fixes + backups + monitoring + cloud deployment + local BAT package + release documentation

Delivery targets:
- 4 weeks: possible for strict MVP
- 5–6 weeks: safer production-style core release
- 8–12+ weeks: broader enterprise scope

## 11. Governance and Status Model

Status values:
- NOT STARTED
- READY
- IN PROGRESS
- BLOCKED
- READY FOR UAT
- DONE

Recommended workflow:
NOT STARTED -> READY -> IN PROGRESS -> BLOCKED (when dependency exists) -> READY FOR UAT -> UAT PASSED -> DONE

Tracker items should include:
- Task ID
- Phase
- Module
- Description
- Priority
- Owner
- Dependency
- Status
- Start date
- Due date
- Blocker
- UAT status
- Notes

Do not mark a task as done only because the UI exists. It must satisfy project definition of done.

## 12. Final Scope Boundary

### In Scope
- Desktop/browser HIS
- Windows local deployment
- Docker
- .bat launch and control scripts
- Patient Master / Patient 360
- OPD
- Token / QR
- IPD
- Ward / room / bed
- Billing / payment
- Laboratory
- Barcode
- Sample collection
- Result approval
- Reports
- Documents / printing
- RBAC
- Multi-hospital foundation
- Audit
- ABHA / ABDM integration framework
- Cloud deployment

### Deferred
- PWA
- Dedicated mobile apps
- Patient mobile app
- Advanced push experience
- Advanced AI / RAG
- Radiology
- Pharmacy
- Inventory
- Blood Bank
- HR
- Advanced Finance / MIS
- Device / analyzer integrations

This scope boundary protects the 4–6 week delivery target for the two-person team.

## 13. Final One-Line Architecture

Next.js + TypeScript + FastAPI + Python + PostgreSQL + S3-compatible storage + Docker + Vercel / portable container hosting, with a separate integration layer for ABHA/ABDM, payments, and other external services.

The same application should run in both cloud mode and local hospital mode using Docker and .bat scripts without rebuilding the core product.

## 14. Contribution Notes

This project should be implemented using the following core principles:
- Keep backend portable and environment-agnostic.
- Use modular domain structure for hospital features.
- Enforce strict tenant/facility boundaries.
- Prefer explicit APIs, validations, and audit continuity.
- Treat local deployment and cloud deployment as parallel operational modes, not separate products.
- Keep integration adapters isolated behind interfaces.
- Make ABHA/ABDM and payment connectors pluggable and non-invasive to the core domain logic.

## 15. Recommended Starting Implementation Order

1. Project foundation and environment setup
2. Authentication, RBAC, and tenant/facility context
3. Patient master and Patient 360
4. OPD + token + QR workflow
5. IPD and bed workflow
6. Billing and payment
7. Laboratory and barcode/sample flow
8. Documents and print templates
9. ABHA/ABDM adapter layer
10. Security, audit, and hardening
11. UAT and deployment

This document serves as the canonical project reference for future contributions and technical decisions.
