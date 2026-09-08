import { ROLES, UserRole } from "@/lib/constants";

export interface Tenant {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
}

export interface Facility {
  id: string;
  tenant_id: string;
  name: string;
  facility_code: string;
  address?: string;
  phone?: string;
  timezone: string;
  currency: string;
  is_active: boolean;
}

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  permissions: string[];
  tenant_id: string;
  facility_id: string;
  is_active: boolean;
}

/** Raw `/auth/login` and `/auth/me` user shape - `role` is nested, not flattened. */
export interface BackendUserPayload {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: { id: string; code: UserRole; name: string; description?: string };
  permissions: string[];
  tenant_id: string;
  facility_id: string;
  is_active: boolean;
}

export function adaptBackendUser(raw: BackendUserPayload): AuthUser {
  return {
    id: raw.id,
    username: raw.username,
    email: raw.email,
    full_name: raw.full_name,
    role: raw.role.code,
    permissions: raw.permissions,
    tenant_id: raw.tenant_id,
    facility_id: raw.facility_id,
    is_active: raw.is_active,
  };
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface AuthSession {
  user: AuthUser;
  tenant: Tenant;
  facility: Facility;
  tokens: AuthTokens;
}

export interface LoginCredentials {
  username: string;
  password: string;
  facility_id?: string;
  remember_me?: boolean;
}

export interface ChangePasswordInput {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface ForgotPasswordInput {
  identifier: string;
  facility_id?: string;
}

export interface ResetPasswordInput {
  token: string;
  new_password: string;
  confirm_password: string;
}

export interface RoleMetadata {
  label: string;
  description: string;
  badgeClassName: string;
  keyPermissions: string[];
}

export const ROLE_METADATA_MAP: Record<UserRole, RoleMetadata> = {
  [ROLES.SUPER_ADMIN]: {
    label: "Super Admin",
    description: "Multi-tenant setup, facility provisioning, system diagnostics.",
    badgeClassName: "bg-purple-100 text-purple-700 border-purple-200",
    keyPermissions: ["Manage tenants & facilities", "Global configuration", "System diagnostics"],
  },
  [ROLES.HOSPITAL_ADMIN]: {
    label: "Hospital Admin",
    description: "User management, doctor/department setup, tariff configuration.",
    badgeClassName: "bg-blue-100 text-blue-700 border-blue-200",
    keyPermissions: ["Manage users", "Configure departments", "Configure tariffs"],
  },
  [ROLES.RECEPTIONIST]: {
    label: "Receptionist / Front Desk",
    description: "Patient registration, OPD booking, and queue management.",
    badgeClassName: "bg-amber-100 text-amber-700 border-amber-200",
    keyPermissions: ["Register patients", "Issue tokens", "Manage OPD queue"],
  },
  [ROLES.BILLING_CASHIER]: {
    label: "Billing / Cashier",
    description: "Invoicing, payment collection, and billing reconciliation.",
    badgeClassName: "bg-orange-100 text-orange-700 border-orange-200",
    keyPermissions: ["Create invoices", "Collect payments", "Print receipts"],
  },
  [ROLES.DOCTOR]: {
    label: "Doctor",
    description: "OPD/IPD consultation, prescriptions, and clinical notes.",
    badgeClassName: "bg-teal-100 text-teal-700 border-teal-200",
    keyPermissions: ["View patient records", "Write prescriptions", "Order lab tests"],
  },
  [ROLES.NURSE]: {
    label: "Nurse",
    description: "Ward rounds, vitals capture, and medication administration.",
    badgeClassName: "bg-pink-100 text-pink-700 border-pink-200",
    keyPermissions: ["Record vitals", "Administer medication", "Update bed status"],
  },
  [ROLES.LAB_TECH]: {
    label: "Lab Technician",
    description: "Sample accessioning, collection, and result entry.",
    badgeClassName: "bg-cyan-100 text-cyan-700 border-cyan-200",
    keyPermissions: ["Accession samples", "Enter results", "Track TAT"],
  },
  [ROLES.LAB_APPROVER]: {
    label: "Lab Approver",
    description: "Clinical verification and final electronic approval of results.",
    badgeClassName: "bg-indigo-100 text-indigo-700 border-indigo-200",
    keyPermissions: ["Verify results", "Amend values", "Approve reports"],
  },
  [ROLES.AUDITOR]: {
    label: "Auditor",
    description: "Read-only access to audit trails and reconciliation reports.",
    badgeClassName: "bg-slate-100 text-slate-700 border-slate-200",
    keyPermissions: ["View audit logs", "View financial reconciliation", "Read-only access"],
  },
};

export interface AuthContextType {
  user: AuthUser | null;
  tenant: Tenant | null;
  facility: Facility | null;
  availableFacilities: Facility[];
  isAuthenticated: boolean;
  isLoading: boolean;
  isUsingMockAuth: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  switchFacility: (facilityId: string) => void;
  changePassword: (input: ChangePasswordInput) => Promise<void>;
  hasRole: (roles?: UserRole[]) => boolean;
  hasPermission: (permission: string) => boolean;
}
