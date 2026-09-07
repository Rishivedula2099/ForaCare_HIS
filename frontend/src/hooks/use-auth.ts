"use client";

import { useAuthContext } from "@/providers/auth-provider";
import { AuthContextType } from "@/types/auth";

/**
 * Access session data, the active tenant/facility, and auth actions
 * (login, logout, switchFacility, changePassword, hasRole, hasPermission).
 */
export function useAuth(): AuthContextType {
  return useAuthContext();
}
