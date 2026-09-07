import { UserRole } from "@/lib/constants";

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
  tenant_id: string;
  facility_id: string;
  is_active: boolean;
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
