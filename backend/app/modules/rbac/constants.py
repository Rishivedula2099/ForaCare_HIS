import enum


class SystemRole(str, enum.Enum):
    """The 9 roles seeded on every environment (see ASM-OPS-01 role review).

    These are bootstrap data, not a fixed enum type in the database -
    `roles` is a real table and additional roles can be added later without
    a code change. Mirrors `ROLES` in frontend/src/lib/constants.ts.
    """

    SUPER_ADMIN = "SUPER_ADMIN"
    HOSPITAL_ADMIN = "HOSPITAL_ADMIN"
    DOCTOR = "DOCTOR"
    NURSE = "NURSE"
    RECEPTIONIST = "RECEPTIONIST"
    BILLING_CASHIER = "BILLING_CASHIER"
    LAB_TECH = "LAB_TECH"
    LAB_APPROVER = "LAB_APPROVER"
    AUDITOR = "AUDITOR"


SYSTEM_ROLE_NAMES: dict[str, str] = {
    SystemRole.SUPER_ADMIN: "Super Admin",
    SystemRole.HOSPITAL_ADMIN: "Hospital Admin",
    SystemRole.DOCTOR: "Doctor",
    SystemRole.NURSE: "Nurse",
    SystemRole.RECEPTIONIST: "Receptionist / Front Desk",
    SystemRole.BILLING_CASHIER: "Billing / Cashier",
    SystemRole.LAB_TECH: "Lab Technician",
    SystemRole.LAB_APPROVER: "Lab Approver",
    SystemRole.AUDITOR: "Auditor",
}

# Stable integer identifiers (per the P1-B07 role review), independent of
# the string `code` (application key) and `name` (UI label) - never used
# for authorization decisions, only as a durable numeric reference.
SYSTEM_ROLE_NUMERIC_CODES: dict[str, int] = {
    SystemRole.SUPER_ADMIN: 1,
    SystemRole.HOSPITAL_ADMIN: 2,
    SystemRole.DOCTOR: 3,
    SystemRole.NURSE: 4,
    SystemRole.RECEPTIONIST: 5,
    SystemRole.BILLING_CASHIER: 6,
    SystemRole.LAB_TECH: 7,
    SystemRole.LAB_APPROVER: 8,
    SystemRole.AUDITOR: 9,
}

# (code, module, description) - a representative starting catalog. Extend as
# real feature modules get built; nothing about the RBAC mechanism assumes
# this list is exhaustive.
PERMISSION_CATALOG: list[tuple[str, str, str]] = [
    ("patients.view", "patients", "View patient records"),
    ("patients.manage", "patients", "Register and update patient records"),
    ("opd.view", "opd", "View OPD encounters, tokens, and the doctor queue"),
    ("opd.manage_queue", "opd", "Manage OPD queue and appointments"),
    ("consultations.view", "opd", "View OPD consultation records and patient history"),
    ("consultations.manage", "opd", "Record and update OPD consultations"),
    ("prescriptions.view", "opd", "View OPD prescriptions"),
    ("prescriptions.manage", "opd", "Create and update OPD prescriptions"),
    ("ipd.view", "ipd", "View IPD wards, rooms, beds, and admissions"),
    ("ipd.manage_beds", "ipd", "Manage IPD wards, rooms, beds, admissions, transfers, and discharges"),
    # Module-level access: opens the Billing module and covers every read
    # endpoint (service/package catalog, invoices, payments, deposits,
    # receipts). Deliberately a single permission, distinct from the
    # per-action ones below - "can see the module" and "can act in it" are
    # different questions, so a role can hold `billing.view` without any of
    # the `*.create` permissions (module access != full billing authority).
    ("billing.view", "billing", "View the billing module - services, packages, invoices, payments, deposits, and receipts"),
    ("billing.manage_services", "billing", "Create and update services and packages"),
    ("billing.invoice.create", "billing", "Create invoices and add line items"),
    ("billing.payment.create", "billing", "Collect payments and deposits"),
    ("billing.refund.create", "billing", "Refund payments and deposits"),
    # Module-level access: opens the Laboratory module and covers every read
    # endpoint (test/parameter/reference-range master, orders, results),
    # distinct from `lab.manage_master`/the per-action codes below - mirrors
    # `billing.view` above (module access != full lab authority).
    ("lab.view", "lab", "View the laboratory module - test master, orders, and results"),
    ("lab.manage_master", "lab", "Create and update the lab test/parameter/reference-range master"),
    ("lab.accession_sample", "lab", "Accession and track lab samples"),
    ("lab.enter_results", "lab", "Enter lab test results"),
    ("lab.verify_results", "lab", "Technically verify lab results"),
    ("lab.approve_reports", "lab", "Approve and release final lab reports"),
    ("departments.view", "departments", "View department master data"),
    ("departments.manage", "departments", "Create and update departments"),
    ("doctors.view", "doctors", "View doctor master data"),
    ("doctors.manage", "doctors", "Create and update doctor records"),
    ("documents.print", "documents", "Print and generate documents"),
    ("audit.view_logs", "audit", "View audit trails and access logs"),
    ("users.manage", "settings", "Manage staff user accounts"),
    ("roles.view", "settings", "View roles and permissions"),
    ("roles.manage", "settings", "Manage role-permission assignments"),
    ("facilities.manage", "settings", "Configure facilities and departments"),
    ("tenants.manage", "settings", "Manage tenants (multi-hospital setup)"),
    ("system.diagnostics", "settings", "View system diagnostics and configuration"),
]

ALL_PERMISSION_CODES: list[str] = [code for code, _, _ in PERMISSION_CATALOG]

# Every role except SUPER_ADMIN (which already gets everything via
# `ALL_PERMISSION_CODES`) and BILLING_CASHIER (whose refund exclusion is a
# deliberate, separately-decided restriction - see below) gets the full
# billing permission set: view + create invoices + collect payments +
# refund + manage the service/package catalog.
_FULL_BILLING_ACCESS = [
    "billing.view",
    "billing.manage_services",
    "billing.invoice.create",
    "billing.payment.create",
    "billing.refund.create",
]

ROLE_PERMISSION_SEED: dict[str, list[str]] = {
    SystemRole.SUPER_ADMIN: ALL_PERMISSION_CODES,
    SystemRole.HOSPITAL_ADMIN: [
        "users.manage",
        "roles.view",
        "roles.manage",
        "facilities.manage",
        "patients.view",
        "departments.view",
        "departments.manage",
        "doctors.view",
        "doctors.manage",
        "opd.view",
        "consultations.view",
        "consultations.manage",
        "prescriptions.view",
        "prescriptions.manage",
        "ipd.view",
        "ipd.manage_beds",
        *_FULL_BILLING_ACCESS,
        "lab.view",
        "lab.manage_master",
        "audit.view_logs",
    ],
    SystemRole.DOCTOR: [
        "patients.view",
        "patients.manage",
        "opd.view",
        "opd.manage_queue",
        "consultations.view",
        "consultations.manage",
        "prescriptions.view",
        "prescriptions.manage",
        "ipd.view",
        "ipd.manage_beds",
        "departments.view",
        "doctors.view",
        "documents.print",
        *_FULL_BILLING_ACCESS,
        "lab.view",
    ],
    SystemRole.NURSE: [
        "patients.view",
        "ipd.view",
        "ipd.manage_beds",
        "departments.view",
        "doctors.view",
        "opd.view",
        "consultations.view",
        "prescriptions.view",
        "documents.print",
        *_FULL_BILLING_ACCESS,
        "lab.view",
    ],
    SystemRole.RECEPTIONIST: [
        "patients.view",
        "patients.manage",
        "opd.view",
        "opd.manage_queue",
        "ipd.view",
        "departments.view",
        "doctors.view",
        "documents.print",
        *_FULL_BILLING_ACCESS,
        "lab.view",
    ],
    # S5-B01: refund authority is deliberately withheld here - a cashier can
    # view the module, create invoices, and collect payments/deposits, but
    # not reverse them. Only HOSPITAL_ADMIN/SUPER_ADMIN get
    # `billing.refund.create` by default; a facility that wants a specific
    # cashier to process refunds grants it explicitly via role management
    # rather than by default for the whole role.
    SystemRole.BILLING_CASHIER: [
        "billing.view",
        "billing.invoice.create",
        "billing.payment.create",
        "documents.print",
    ],
    SystemRole.LAB_TECH: [
        "lab.view",
        "lab.accession_sample",
        "lab.enter_results",
        "documents.print",
        *_FULL_BILLING_ACCESS,
    ],
    SystemRole.LAB_APPROVER: [
        "lab.view",
        "lab.manage_master",
        "lab.verify_results",
        "lab.approve_reports",
        "documents.print",
        *_FULL_BILLING_ACCESS,
    ],
    SystemRole.AUDITOR: ["audit.view_logs", "lab.view", *_FULL_BILLING_ACCESS],
}
