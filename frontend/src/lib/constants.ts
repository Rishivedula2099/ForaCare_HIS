/**
 * ForaCare HIS - Application Constants
 */

export const APP_NAME = "ForaCare HIS";
export const APP_VERSION = "0.1.0-alpha";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const ROLES = {
  SUPER_ADMIN: "SUPER_ADMIN",
  HOSPITAL_ADMIN: "HOSPITAL_ADMIN",
  RECEPTIONIST: "RECEPTIONIST",
  BILLING_CASHIER: "BILLING_CASHIER",
  DOCTOR: "DOCTOR",
  NURSE: "NURSE",
  LAB_TECH: "LAB_TECH",
  LAB_APPROVER: "LAB_APPROVER",
  AUDITOR: "AUDITOR",
} as const;

export type UserRole = (typeof ROLES)[keyof typeof ROLES];

export const TOKEN_STATUS = {
  WAITING: "WAITING",
  CALLED: "CALLED",
  IN_CONSULTATION: "IN_CONSULTATION",
  COMPLETED: "COMPLETED",
  SKIPPED: "SKIPPED",
  CANCELLED: "CANCELLED",
} as const;

export const BED_STATUS = {
  AVAILABLE: "AVAILABLE",
  RESERVED: "RESERVED",
  OCCUPIED: "OCCUPIED",
  CLEANING: "CLEANING",
  MAINTENANCE: "MAINTENANCE",
  BLOCKED: "BLOCKED",
} as const;

export const LAB_ORDER_STATUS = {
  ORDERED: "ORDERED",
  BILLED: "BILLED",
  ACCESSIONED: "ACCESSIONED",
  COLLECTION_PENDING: "COLLECTION_PENDING",
  COLLECTED: "COLLECTED",
  PROCESSING: "PROCESSING",
  RESULT_ENTERED: "RESULT_ENTERED",
  TECHNICALLY_VERIFIED: "TECHNICALLY_VERIFIED",
  PENDING_APPROVAL: "PENDING_APPROVAL",
  APPROVED: "APPROVED",
  FINALIZED: "FINALIZED",
} as const;

export interface NavItem {
  title: string;
  href: string;
  iconName: string;
  badge?: string;
  roles?: UserRole[];
}

export const MAIN_NAV_ITEMS: NavItem[] = [
  {
    title: "Dashboard",
    href: "/dashboard",
    iconName: "LayoutDashboard",
  },
  {
    title: "Patients (360)",
    href: "/patients",
    iconName: "Users",
  },
  {
    title: "OPD & Queue",
    href: "/opd",
    iconName: "CalendarClock",
  },
  {
    title: "IPD & Beds",
    href: "/ipd",
    iconName: "BedDouble",
  },
  {
    title: "Billing & Cashier",
    href: "/billing",
    iconName: "Receipt",
  },
  {
    title: "Laboratory",
    href: "/laboratory",
    iconName: "FlaskConical",
  },
  {
    title: "Documents",
    href: "/documents",
    iconName: "Printer",
  },
  {
    title: "Audit & Logs",
    href: "/audit",
    iconName: "ShieldCheck",
    roles: [ROLES.SUPER_ADMIN, ROLES.HOSPITAL_ADMIN, ROLES.AUDITOR],
  },
  {
    title: "Settings",
    href: "/settings",
    iconName: "SlidersHorizontal",
    roles: [ROLES.SUPER_ADMIN, ROLES.HOSPITAL_ADMIN],
  },
  {
    title: "Roles & Permissions",
    href: "/roles",
    iconName: "KeyRound",
    roles: [ROLES.SUPER_ADMIN, ROLES.HOSPITAL_ADMIN],
  },
];
