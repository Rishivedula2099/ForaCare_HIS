# ForaCare HIS – External Integrations Register
**Document Reference:** `docs/integrations.md`  
**Status:** ACTIVE  
**Lifecycle Stage:** Phase 0 – Requirements & Readiness  

---

## 1. Overview & Architecture Strategy

In accordance with Section 2, 4, and 14 of `context.md`, all external integrations must adhere to the **Pluggable Adapter Pattern**.
- Domain services interact exclusively with abstract Python Protocol / ABC interfaces.
- Each integration provider implements an adapter satisfying the interface.
- Core business logic (Patient Registration, Billing, Lab, OPD) has zero direct dependencies on external vendor SDKs or specific cloud APIs.
- Phase 1 delivers **Mock Adapters** allowing full end-to-end development, testing, and offline hospital execution without blocking on external credential procurement.

---

## 2. External API Integration Records

### 2.1. ABDM / ABHA – Milestone 1 (M1: Identity Creation & Verification)

* **Provider:** National Health Authority (NHA) / Ayushman Bharat Digital Mission (ABDM)
* **Purpose:** Patient ABHA ID / ABHA Address generation via Aadhaar OTP, Mobile OTP, and biometric verification; demographic verification.
* **Sandbox URL:** `https://dev.abdm.gov.in/gateway/v0.5`
* **Production URL:** `https://gateway.abdm.gov.in/v0.5`
* **Authentication Method:** OAuth 2.0 (Client ID + Client Secret $\rightarrow$ Gateway Bearer Token) with RSA PKI payload encryption.
* **Test Credential Status:** TBD (Pending NHA Sandbox Developer Portal enrollment)
* **Production Credential Status:** TBD (Requires NHA empanelment and security audit certification)
* **Webhook Requirement:** Yes (`/api/v1/integrations/abdm/v0.5/users/auth/on-confirm`, etc. - asynchronous callback architecture)
* **Owner / Contact:** Dev 1 (Technical Adapter) / Production Owner (NHA Liaison)
* **Dependency:** Internet connectivity on host server; public HTTPS endpoint or reverse proxy for ABDM callbacks.
* **Target Phase:** Phase 8 (Mock in Phase 1-7)

---

### 2.2. ABDM / ABHA – Milestone 2 (M2: Link & Discover Health Records)

* **Provider:** National Health Authority (NHA) / ABDM
* **Purpose:** Discover patient records by Patient UID / ABHA, issue link tokens, and link OPD/IPD/Lab clinical records to patient's ABHA address.
* **Sandbox URL:** `https://dev.abdm.gov.in/gateway/v0.5`
* **Production URL:** `https://gateway.abdm.gov.in/v0.5`
* **Authentication Method:** OAuth 2.0 Bearer Token + Gateway Session Headers.
* **Test Credential Status:** TBD
* **Production Credential Status:** TBD
* **Webhook Requirement:** Yes (`/api/v1/integrations/abdm/v0.5/care-contexts/discover`, `/care-contexts/link`)
* **Owner / Contact:** Dev 1
* **Dependency:** ABDM M1 completion, Patient Master with ABHA linkage fields.
* **Target Phase:** Phase 8 (Mock in Phase 1-7)

---

### 2.3. ABDM / ABHA – Milestone 3 (M3: Health Information Exchange / FHIR)

* **Provider:** National Health Authority (NHA) / ABDM
* **Purpose:** Consent manager request processing, encryption/decryption of clinical artifacts, FHIR Bundle export (OPD Prescription, Lab Report, Discharge Summary).
* **Sandbox URL:** `https://dev.abdm.gov.in/gateway/v0.5`
* **Production URL:** `https://gateway.abdm.gov.in/v0.5`
* **Authentication Method:** OAuth 2.0 + Diffie-Hellman Key Exchange for encrypted health data transfer.
* **Test Credential Status:** TBD
* **Production Credential Status:** TBD
* **Webhook Requirement:** Yes (`/api/v1/integrations/abdm/v0.5/consent-requests/on-init`, `/data-flow/data-push`)
* **Owner / Contact:** Dev 1
* **Dependency:** ABDM M2, Clinical data models matching NRCES FHIR profiles.
* **Target Phase:** Phase 8 (Mock in Phase 1-7)

---

### 2.4. Payment Gateway (Online / Dynamic UPI QR)

* **Provider:** Razorpay / Pine Labs / Cashfree (TBD by Production Owner)
* **Purpose:** Generate dynamic UPI payment QR codes on reception and cashier screens; collect online invoice payments; initiate refunds.
* **Sandbox URL:** TBD (e.g., `https://api.razorpay.com/v1` for test mode)
* **Production URL:** TBD
* **Authentication Method:** HTTP Basic Auth (API Key ID + Secret) or Bearer Token.
* **Test Credential Status:** TBD
* **Production Credential Status:** TBD
* **Webhook Requirement:** Yes (Signature-verified payment capture webhook: `/api/v1/integrations/payments/webhook`)
* **Owner / Contact:** Dev 1 / Production Owner
* **Dependency:** Active business bank account and merchant onboarding.
* **Target Phase:** Phase 5 (Manual payment recording supported in Phase 1; Gateway in Phase 5)

---

### 2.5. SMS Notification Gateway

* **Provider:** TBD (e.g., MSG91 / Twilio / NIC SMS Gateway)
* **Purpose:** Send OPD Token alerts, registration confirmation with Patient UID, and lab report ready download links.
* **Sandbox URL:** TBD
* **Production URL:** TBD
* **Authentication Method:** API Key / Auth Header / DLT Registration Template Headers.
* **Test Credential Status:** TBD
* **Production Credential Status:** TBD
* **Webhook Requirement:** No (Asynchronous outbound HTTP requests; delivery receipts optional)
* **Owner / Contact:** Dev 1 / Production Owner
* **Dependency:** Telecom DLT (Distributed Ledger Technology) Entity and SMS Header approval in India.
* **Target Phase:** Phase 5 (Mock console logger in Phase 1)

---

### 2.6. WhatsApp Business Cloud API

* **Provider:** Meta Cloud API / Gupshup / Infobip (TBD)
* **Purpose:** Automated delivery of digital PDF receipts, OPD token status, and lab reports directly to patient WhatsApp number.
* **Sandbox URL:** `https://graph.facebook.com/v19.0` (TBD)
* **Production URL:** `https://graph.facebook.com/v19.0` (TBD)
* **Authentication Method:** Bearer Access Token (System User Token) + Phone Number ID.
* **Test Credential Status:** TBD
* **Production Credential Status:** TBD
* **Webhook Requirement:** Yes (Status callbacks and inbound interactive message triggers)
* **Owner / Contact:** Dev 1 / Production Owner
* **Dependency:** Meta Business Verification and approved WhatsApp message templates.
* **Target Phase:** Phase 7 / Deferred Phase

---

### 2.7. Email Gateway (SMTP / API)

* **Provider:** AWS SES / SendGrid / Hospital Exchange SMTP Server (TBD)
* **Purpose:** Daily cashier closing reports, password resets, system error alerts to hospital admin.
* **Sandbox URL:** TBD (Local SMTP sink e.g. Mailhog or test account)
* **Production URL:** TBD
* **Authentication Method:** SMTP Auth (Username/Password) or API Bearer Token.
* **Test Credential Status:** TBD
* **Production Credential Status:** TBD
* **Webhook Requirement:** No (Bounce / complaint handling optional)
* **Owner / Contact:** Dev 1
* **Dependency:** Domain DNS verification (SPF, DKIM, DMARC).
* **Target Phase:** Phase 1 (Local SMTP sink or console logging for dev)

---

### 2.8. Object Storage Service (S3-Compatible)

* **Provider:** Cloudflare R2 / AWS S3 / Local MinIO (Local deployment)
* **Purpose:** Permanent archival of generated Lab Report PDFs, Patient ID scans, IPD Admission and Discharge PDFs.
* **Sandbox URL:** `http://localhost:9000` (Local MinIO or local filesystem driver)
* **Production URL:** TBD
* **Authentication Method:** AWS S3 Signature v4 (Access Key ID + Secret Access Key + Region + Bucket).
* **Test Credential Status:** AVAILABLE (Local filesystem / local MinIO container ready)
* **Production Credential Status:** TBD
* **Webhook Requirement:** No
* **Owner / Contact:** Dev 1
* **Dependency:** Storage bucket provisioning and CORS / presigned URL configuration.
* **Target Phase:** Phase 1 (Filesystem/MinIO in Phase 1; Cloudflare R2/S3 in Phase 11)

---

## 3. Summary Integration Matrix

| Integration | Provider | Purpose | Test Credential Status | Prod Credential Status | Target Phase | Owner |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **ABDM M1** | NHA | ABHA Creation & KYC | TBD | TBD | Phase 8 (Mock: Phase 1) | Dev 1 |
| **ABDM M2** | NHA | Care Context Linking | TBD | TBD | Phase 8 (Mock: Phase 1) | Dev 1 |
| **ABDM M3** | NHA | FHIR Data Transfer | TBD | TBD | Phase 8 (Mock: Phase 1) | Dev 1 |
| **Payment Gateway** | TBD | Online / UPI QR Billing | TBD | TBD | Phase 5 | Dev 1 |
| **SMS Gateway** | TBD | Patient Alerts / Tokens | TBD | TBD | Phase 5 | Dev 1 |
| **WhatsApp API** | TBD | PDF Reports to Phone | TBD | TBD | Phase 7 (Deferred) | Dev 1 |
| **Email Gateway** | TBD | System & Shift Reports | TBD | TBD | Phase 1 | Dev 1 |
| **Object Storage** | MinIO / S3 | Report & Document Store | AVAILABLE (Local) | TBD | Phase 1 | Dev 1 |
