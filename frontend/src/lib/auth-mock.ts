/**
 * Mock auth fallback used when the real backend (`/api/v1/auth/*`) is
 * unreachable, so all 8 clinical roles can be exercised in the UI without
 * a running backend. IDs mirror the backend's seed migration
 * (`backend/migrations/versions/..._seed_demo_tenant_facilities_users.py`)
 * so switching between mock and real auth is seamless.
 */
import { ROLES, UserRole } from "@/lib/constants";
import { AuthSession, AuthUser, Facility, Tenant } from "@/types/auth";

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

export const MOCK_STAFF_DIRECTORY: MockStaffMember[] = [
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333301",
      username: "super.admin",
      email: "super.admin@foracare-his.com",
      full_name: "Ananya Kapoor",
      role: ROLES.SUPER_ADMIN,
      tenant_id: MOCK_TENANT.id,
      facility_id: MAIN_FACILITY_ID,
      is_active: true,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333302",
      username: "hospital.admin",
      email: "hospital.admin@foracare-his.com",
      full_name: "Vikram Seth",
      role: ROLES.HOSPITAL_ADMIN,
      tenant_id: MOCK_TENANT.id,
      facility_id: MAIN_FACILITY_ID,
      is_active: true,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333303",
      username: "receptionist",
      email: "rahul.deshmukh@foracare-his.com",
      full_name: "Rahul Deshmukh",
      role: ROLES.RECEPTIONIST,
      tenant_id: MOCK_TENANT.id,
      facility_id: MAIN_FACILITY_ID,
      is_active: true,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333304",
      username: "dr.priya",
      email: "priya.raman@foracare-his.com",
      full_name: "Dr. Priya Raman",
      role: ROLES.DOCTOR,
      tenant_id: MOCK_TENANT.id,
      facility_id: MAIN_FACILITY_ID,
      is_active: true,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333305",
      username: "nurse.mary",
      email: "mary.joseph@foracare-his.com",
      full_name: "Sister Mary Joseph",
      role: ROLES.NURSE,
      tenant_id: MOCK_TENANT.id,
      facility_id: MAIN_FACILITY_ID,
      is_active: true,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333306",
      username: "lab.tech",
      email: "lab.tech@foracare-his.com",
      full_name: "Sanjay Iyer",
      role: ROLES.LAB_TECH,
      tenant_id: MOCK_TENANT.id,
      facility_id: METRO_FACILITY_ID,
      is_active: true,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333307",
      username: "lab.approver",
      email: "anirudh.sen@foracare-his.com",
      full_name: "Dr. Anirudh Sen",
      role: ROLES.LAB_APPROVER,
      tenant_id: MOCK_TENANT.id,
      facility_id: METRO_FACILITY_ID,
      is_active: true,
    },
  },
  {
    password: "Demo@123",
    user: {
      id: "33333333-3333-3333-3333-333333333308",
      username: "auditor",
      email: "auditor@foracare-his.com",
      full_name: "Meera Nair",
      role: ROLES.AUDITOR,
      tenant_id: MOCK_TENANT.id,
      facility_id: SOUTH_FACILITY_ID,
      is_active: true,
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

function generateMockToken(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
}

export function findFacilityById(facilityId: string): Facility | undefined {
  return MOCK_FACILITIES.find((facility) => facility.id === facilityId);
}

/**
 * TODO(temporary): sign-in is bypassed for local development, mirroring
 * the backend's dev-only bypass (see
 * `backend/app/modules/auth/service.py::authenticate_user`) - any
 * email/username + any password succeeds. A known username/email logs in
 * as that staff member; anything else falls back to the first demo user.
 * Restore the exact-match check below before enabling real auth.
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
    tokens: {
      access_token: generateMockToken("mock_access"),
      refresh_token: generateMockToken("mock_refresh"),
      token_type: "bearer",
      expires_in: 30 * 60,
    },
  };
}
