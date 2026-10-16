import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/api";

export interface OptionPair {
  value: string;
  label: string;
}

export interface SetupOptions {
  facility_types: OptionPair[];
  timezones: OptionPair[];
  currencies: OptionPair[];
  email_delivery_available: boolean;
  default_timezone: string;
  default_currency: string;
}

export interface TenantSetupInput {
  organization: { name: string; code: string };
  facility: {
    name: string;
    facility_code: string;
    facility_type: string;
    phone: string;
    email: string;
    address_line1: string;
    address_line2: string | null;
    city: string;
    state: string;
    postal_code: string;
    timezone: string;
    currency: string;
  };
  administrator: { full_name: string; username: string; email: string };
  send_activation_email: boolean;
}

export interface SetupResult {
  tenant_id: string;
  tenant_code: string;
  tenant_name: string;
  facility_id: string;
  facility_code: string;
  facility_name: string;
  facility_type: string;
  administrator_username: string;
  administrator_email: string;
  activation_link: string;
  activation_expires_hours: number;
  activation_email_sent: boolean;
}

/** true = free, false = taken, null = not asked. */
export interface Availability {
  organization_code: boolean | null;
  facility_code: boolean | null;
  username: boolean | null;
  email: boolean | null;
}

function unwrap<T>(response: ApiResponse<T>): T {
  if (!response.data) throw new Error("Empty response from server.");
  return response.data;
}

export async function getSetupOptions(): Promise<SetupOptions> {
  return unwrap(await apiClient.get<SetupOptions>("/platform/setup-options"));
}

export async function checkAvailability(params: {
  organization_code?: string;
  facility_code?: string;
  username?: string;
  email?: string;
}): Promise<Availability> {
  const query = Object.fromEntries(Object.entries(params).filter(([, v]) => v));
  return unwrap(await apiClient.get<Availability>("/platform/setup/availability", { params: query }));
}

export async function createTenant(input: TenantSetupInput): Promise<SetupResult> {
  return unwrap(await apiClient.post<SetupResult>("/platform/tenants", input));
}
