/**
 * Mock auth fallback used when the real backend (`/api/v1/auth/*`) is
 * unreachable, so all 8 clinical roles can be exercised in the UI without
 * a running backend. IDs mirror the backend's seed migration
 * (`backend/migrations/versions/..._seed_demo_tenant_facilities_users.py`)
 * so switching between mock and real auth is seamless.
 */
import { ROLES, UserRole } from "@/lib/constants";
import { AuthSession, AuthUser, Facility, Tenant } from "@/types/auth";

/** Mirrors the backend's ROLE_PERMISSION_SEED (app/modules/rbac/constants.py). */
const MOCK_ROLE_PERMISSIONS: Record<UserRole, string[]> = {
  [ROLES.SUPER_ADMIN]: [
    "patients.view", "patients.manage", "opd.manage_queue", "ipd.manage_beds",
    "billing.create_invoice", "billing.collect_payment", "lab.accession_sample",
    "lab.enter_results", "lab.verify_results", "lab.approve_reports", "documents.print",
    "audit.view_logs", "users.manage", "roles.view", "roles.manage", "facilities.manage",
    "tenants.manage", "system.diagnostics",
  ],
  [ROLES.HOSPITAL_ADMIN]: [
    "users.manage", "roles.view", "roles.manage", "facilities.manage", "patients.view",
    "audit.view_logs",
  ],
  [ROLES.DOCTOR]: ["patients.view", "patients.manage", "opd.manage_queue", "ipd.manage_beds", "documents.print"],
  [ROLES.NURSE]: ["patients.view", "ipd.manage_beds", "documents.print"],
  [ROLES.RECEPTIONIST]: ["patients.view", "patients.manage", "opd.manage_queue", "documents.print"],
  [ROLES.BILLING_CASHIER]: ["billing.create_invoice", "billing.collect_payment", "documents.print"],
  [ROLES.LAB_TECH]: ["lab.accession_sample", "lab.enter_results", "documents.print"],
  [ROLES.LAB_APPROVER]: ["lab.verify_results", "lab.approve_reports", "documents.print"],
  [ROLES.AUDITOR]: ["audit.view_logs"],
};

export const MOCK_TENANT: Tenant = {
  id: "11111111-1111-1111-1111-111111111111",
  name: "ForaCare Health Network",
  code: "FORACARE",
  is_active: true,
};

export const MOCK_FACILITIES: Facility[] = [
  {
    id: "22222222-2222-2222-2222-222222222201",
    tenant_id: MOCK_TENANT.id,
    name: "ForaCare City Hospital (Main Branch)",
    facility_code: "FC-MAIN-01",
    timezone: "Asia/Kolkata",
    currency: "INR",
    is_active: true,
  },
  {
    id: "22222222-2222-2222-2222-222222222202",
    tenant_id: MOCK_TENANT.id,
    name: "ForaCare South Clinic",
    facility_code: "FC-ST-02",
    timezone: "Asia/Kolkata",
    currency: "INR",
    is_active: true,
  },
  {
    id: "22222222-2222-2222-2222-222222222203",
    tenant_id: MOCK_TENANT.id,
    name: "ForaCare Metro Diagnostic Center",
    facility_code: "FC-METRO-03",
    timezone: "Asia/Kolkata",
    currency: "INR",
    is_active: true,
  },
];

interface MockStaffMember {
  user: AuthUser;
  password: string;
}

const MAIN_FACILITY_ID = MOCK_FACILITIES[0].id;
const METRO_FACILITY_ID = MOCK_FACILITIES[2].id;
const SOUTH_FACILITY_ID = MOCK_FACILITIES[1].id;

/** Mirrors app/modules/rbac/constants.py::SYSTEM_ROLE_NUMERIC_CODES. */
const MOCK_ROLE_NUMERIC_CODES: Record<UserRole, number> = {
  [ROLES.SUPER_ADMIN]: 1,
  [ROLES.HOSPITAL_ADMIN]: 2,
  [ROLES.DOCTOR]: 3,
  [ROLES.NURSE]: 4,
  [ROLES.RECEPTIONIST]: 5,
  [ROLES.BILLING_CASHIER]: 6,
  [ROLES.LAB_TECH]: 7,
  [ROLES.LAB_APPROVER]: 8,
  [ROLES.AUDITOR]: 9,
};

export const MOCK_STAFF_DIRECTORY: MockStaffMember[] = [
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333301",
      username: "super.admin",
      email: "super.admin@foracare-his.com",
      phone: null,
      full_name: "Ananya Kapoor",
      role: ROLES.SUPER_ADMIN,
      roleNumericCode: MOCK_ROLE_NUMERIC_CODES[ROLES.SUPER_ADMIN],
      permissions: MOCK_ROLE_PERMISSIONS[ROLES.SUPER_ADMIN],
      tenant_id: MOCK_TENANT.id,
      facility_id: MAIN_FACILITY_ID,
      is_active: true,
      email_verified: true,
      phone_verified: false,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333302",
      username: "hospital.admin",
      email: "hospital.admin@foracare-his.com",
      phone: null,
      full_name: "Vikram Seth",
      role: ROLES.HOSPITAL_ADMIN,
      roleNumericCode: MOCK_ROLE_NUMERIC_CODES[ROLES.HOSPITAL_ADMIN],
      permissions: MOCK_ROLE_PERMISSIONS[ROLES.HOSPITAL_ADMIN],
      tenant_id: MOCK_TENANT.id,
      facility_id: MAIN_FACILITY_ID,
      is_active: true,
      email_verified: true,
      phone_verified: false,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333303",
      username: "receptionist",
      email: "rahul.deshmukh@foracare-his.com",
      phone: null,
      full_name: "Rahul Deshmukh",
      role: ROLES.RECEPTIONIST,
      roleNumericCode: MOCK_ROLE_NUMERIC_CODES[ROLES.RECEPTIONIST],
      permissions: MOCK_ROLE_PERMISSIONS[ROLES.RECEPTIONIST],
      tenant_id: MOCK_TENANT.id,
      facility_id: MAIN_FACILITY_ID,
      is_active: true,
      email_verified: true,
      phone_verified: false,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333309",
      username: "billing.cashier",
      email: "billing.cashier@foracare-his.com",
      phone: null,
      full_name: "Kavita Menon",
      role: ROLES.BILLING_CASHIER,
      roleNumericCode: MOCK_ROLE_NUMERIC_CODES[ROLES.BILLING_CASHIER],
      permissions: MOCK_ROLE_PERMISSIONS[ROLES.BILLING_CASHIER],
      tenant_id: MOCK_TENANT.id,
      facility_id: MAIN_FACILITY_ID,
      is_active: true,
      email_verified: true,
      phone_verified: false,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333304",
      username: "dr.priya",
      email: "priya.raman@foracare-his.com",
      phone: null,
      full_name: "Dr. Priya Raman",
      role: ROLES.DOCTOR,
      roleNumericCode: MOCK_ROLE_NUMERIC_CODES[ROLES.DOCTOR],
      permissions: MOCK_ROLE_PERMISSIONS[ROLES.DOCTOR],
      tenant_id: MOCK_TENANT.id,
      facility_id: MAIN_FACILITY_ID,
      is_active: true,
      email_verified: true,
      phone_verified: false,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333305",
      username: "nurse.mary",
      email: "mary.joseph@foracare-his.com",
      phone: null,
      full_name: "Sister Mary Joseph",
      role: ROLES.NURSE,
      roleNumericCode: MOCK_ROLE_NUMERIC_CODES[ROLES.NURSE],
      permissions: MOCK_ROLE_PERMISSIONS[ROLES.NURSE],
      tenant_id: MOCK_TENANT.id,
      facility_id: MAIN_FACILITY_ID,
      is_active: true,
      email_verified: true,
      phone_verified: false,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333306",
      username: "lab.tech",
      email: "lab.tech@foracare-his.com",
      phone: null,
      full_name: "Sanjay Iyer",
      role: ROLES.LAB_TECH,
      roleNumericCode: MOCK_ROLE_NUMERIC_CODES[ROLES.LAB_TECH],
      permissions: MOCK_ROLE_PERMISSIONS[ROLES.LAB_TECH],
      tenant_id: MOCK_TENANT.id,
      facility_id: METRO_FACILITY_ID,
      is_active: true,
      email_verified: true,
      phone_verified: false,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333307",
      username: "lab.approver",
      email: "anirudh.sen@foracare-his.com",
      phone: null,
      full_name: "Dr. Anirudh Sen",
      role: ROLES.LAB_APPROVER,
      roleNumericCode: MOCK_ROLE_NUMERIC_CODES[ROLES.LAB_APPROVER],
      permissions: MOCK_ROLE_PERMISSIONS[ROLES.LAB_APPROVER],
      tenant_id: MOCK_TENANT.id,
      facility_id: METRO_FACILITY_ID,
      is_active: true,
      email_verified: true,
      phone_verified: false,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333308",
      username: "auditor",
      email: "auditor@foracare-his.com",
      phone: null,
      full_name: "Meera Nair",
      role: ROLES.AUDITOR,
      roleNumericCode: MOCK_ROLE_NUMERIC_CODES[ROLES.AUDITOR],
      permissions: MOCK_ROLE_PERMISSIONS[ROLES.AUDITOR],
      tenant_id: MOCK_TENANT.id,
      facility_id: SOUTH_FACILITY_ID,
      is_active: true,
      email_verified: true,
      phone_verified: false,
    },
  },
];

export interface DemoPreset {
  role: UserRole;
  label: string;
  username: string;
  password: string;
}

export const DEMO_PRESETS: DemoPreset[] = MOCK_STAFF_DIRECTORY.map(({ user, password }) => ({
  role: user.role,
  label: user.full_name,
  username: user.username,
  password,
}));

export function findFacilityById(facilityId: string): Facility | undefined {
  return MOCK_FACILITIES.find((facility) => facility.id === facilityId);
}

/**
 * Offline demo fallback only - used when the real backend is unreachable
 * (network error), never as a substitute for real authentication when the
 * backend is up. Any password matches a known username/email so every
 * clinical role can be demoed without a running backend; unknown input
 * falls back to the first demo user. There is no token of any kind here -
 * real sessions are HttpOnly cookies set by the backend (S1-F01), and this
 * mock path never talks to a real server, so it has nothing to store.
 */
export async function mockLogin(username: string, password: string): Promise<AuthSession> {
  await new Promise((resolve) => setTimeout(resolve, 400));
  void password;

  const match =
    MOCK_STAFF_DIRECTORY.find(
      (entry) => entry.user.username === username || entry.user.email === username
    ) ?? MOCK_STAFF_DIRECTORY[0];

  const facility = findFacilityById(match.user.facility_id) ?? MOCK_FACILITIES[0];

  return {
    user: match.user,
    tenant: MOCK_TENANT,
    facility,
    session: {
      token_type: "bearer",
      expires_in: 15 * 60,
    },
  };
}
