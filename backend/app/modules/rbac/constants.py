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

# (code, module, description) - a representative starting catalog. Extend as
# real feature modules get built; nothing about the RBAC mechanism assumes
# this list is exhaustive.
PERMISSION_CATALOG: list[tuple[str, str, str]] = [
    ("patients.view", "patients", "View patient records"),
    ("patients.manage", "patients", "Register and update patient records"),
    ("opd.manage_queue", "opd", "Manage OPD queue and appointments"),
    ("ipd.manage_beds", "ipd", "Manage IPD beds and admissions"),
    ("billing.create_invoice", "billing", "Create invoices and charges"),
    ("billing.collect_payment", "billing", "Collect and reconcile payments"),
    ("lab.accession_sample", "lab", "Accession and track lab samples"),
    ("lab.enter_results", "lab", "Enter lab test results"),
    ("lab.verify_results", "lab", "Technically verify lab results"),
    ("lab.approve_reports", "lab", "Approve and release final lab reports"),
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

ROLE_PERMISSION_SEED: dict[str, list[str]] = {
    SystemRole.SUPER_ADMIN: ALL_PERMISSION_CODES,
    SystemRole.HOSPITAL_ADMIN: [
        "users.manage",
        "roles.view",
        "roles.manage",
        "facilities.manage",
        "patients.view",
        "audit.view_logs",
    ],
    SystemRole.DOCTOR: [
        "patients.view",
        "patients.manage",
        "opd.manage_queue",
        "ipd.manage_beds",
        "documents.print",
    ],
    SystemRole.NURSE: ["patients.view", "ipd.manage_beds", "documents.print"],
    SystemRole.RECEPTIONIST: [
        "patients.view",
        "patients.manage",
        "opd.manage_queue",
        "documents.print",
    ],
    SystemRole.BILLING_CASHIER: [
        "billing.create_invoice",
        "billing.collect_payment",
        "documents.print",
    ],
    SystemRole.LAB_TECH: ["lab.accession_sample", "lab.enter_results", "documents.print"],
    SystemRole.LAB_APPROVER: ["lab.verify_results", "lab.approve_reports", "documents.print"],
    SystemRole.AUDITOR: ["audit.view_logs"],
}
