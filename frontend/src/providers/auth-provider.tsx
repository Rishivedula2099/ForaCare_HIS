"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/types/api";
import {
  adaptBackendUser,
  AuthContextType,
  AuthError,
  AuthUser,
  BackendUserPayload,
  ChangePasswordInput,
  Facility,
  LoginCredentials,
  LoginFailureCode,
  Tenant,
} from "@/types/auth";
import { useToast } from "@/hooks/use-toast";

// Sessions are HttpOnly cookies set by the backend (S1-F01). Nothing about
// them - and no credential of any kind - is ever stored in the browser.

const IDLE_LIMIT_MS = 15 * 60 * 1000;
const IDLE_WARNING_MS = 60 * 1000;
const ACTIVITY_EVENTS: (keyof WindowEventMap)[] = ["mousemove", "mousedown", "keydown", "scroll", "touchstart"];

/** Shape of `/auth/login`, `/auth/me` and `/auth/switch-facility` data. */
interface SessionResponseData {
  user: BackendUserPayload;
  tenant: Tenant;
  facility: Facility;
  /** Every facility the user holds a membership in. */
  facilities: Facility[];
}

interface SessionTimeoutState {
  isWarningVisible: boolean;
  secondsRemaining: number;
}

interface InternalAuthContextType extends AuthContextType {
  sessionTimeout: SessionTimeoutState;
  extendSession: () => void;
}

const AuthContext = React.createContext<InternalAuthContextType | null>(null);

/** Maps a backend error onto the sign-in failure states the UI distinguishes. */
function toAuthError(error: unknown): AuthError {
  const apiError = error as Partial<ApiError>;
  switch (apiError?.code) {
    case "ACCOUNT_DISABLED":
      return new AuthError(apiError.message || "This account is disabled.", "ACCOUNT_DISABLED");
    case "NO_FACILITY_ACCESS":
    case "FACILITY_NOT_ASSIGNED":
      return new AuthError(apiError.message || "No facility access.", apiError.code as LoginFailureCode);
    case "NETWORK_ERROR":
    case "TIMEOUT":
      return new AuthError("Unable to reach the server. Check your connection and try again.", "NETWORK_ERROR");
  }
  if (apiError?.status_code === 429) {
    return new AuthError("Too many attempts. Please wait a minute and try again.", "TOO_MANY_REQUESTS");
  }
  if (apiError?.status_code === 401) {
    return new AuthError("Invalid username or password.", "INVALID_CREDENTIALS");
  }
  return new AuthError(apiError?.message || "Unable to sign in. Please try again.", "UNKNOWN");
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [user, setUser] = React.useState<AuthUser | null>(null);
  const [tenant, setTenant] = React.useState<Tenant | null>(null);
  const [facility, setFacility] = React.useState<Facility | null>(null);
  const [facilities, setFacilities] = React.useState<Facility[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [sessionTimeout, setSessionTimeout] = React.useState<SessionTimeoutState>({
    isWarningVisible: false,
    secondsRemaining: IDLE_WARNING_MS / 1000,
  });

  const lastActivityRef = React.useRef<number>(0);
  const isAuthenticatedRef = React.useRef(false);

  const applySession = React.useCallback((data: SessionResponseData): AuthUser => {
    const adapted = adaptBackendUser(data.user);
    setUser(adapted);
    setTenant(data.tenant);
    setFacility(data.facility);
    setFacilities(data.facilities?.length ? data.facilities : [data.facility]);
    return adapted;
  }, []);

  // Hydrate on mount. The session lives in HttpOnly cookies the browser
  // already sent with this call - there is no client-side token to read - so
  // we simply ask the backend who (if anyone) is authenticated. A 401 just
  // means "not signed in".
  React.useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      lastActivityRef.current = Date.now();
      try {
        const response = await apiClient.get<SessionResponseData>("/auth/me");
        if (!cancelled && response.data) applySession(response.data);
      } catch {
        // Not signed in (or the backend is unreachable): stay signed out.
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void hydrate();
    return () => {
      cancelled = true;
    };
  }, [applySession]);

  React.useEffect(() => {
    isAuthenticatedRef.current = !!user;
  }, [user]);

  const logout = React.useCallback(
    async (reason: "idle" | "manual" = "manual") => {
      try {
        await apiClient.post("/auth/logout");
      } catch {
        // best-effort - still clear local state below even if the server call fails.
      }
      // Drop every cached response: the next person on this browser must not
      // see the previous user's patient/billing/lab data (P9-F03).
      queryClient.clear();
      setUser(null);
      setTenant(null);
      setFacility(null);
      setFacilities([]);
      setSessionTimeout({ isWarningVisible: false, secondsRemaining: IDLE_WARNING_MS / 1000 });
      router.push(reason === "idle" ? "/login?reason=idle" : "/login");
    },
    [router, queryClient]
  );

  const login = React.useCallback(
    async (credentials: LoginCredentials): Promise<AuthUser> => {
      let data: SessionResponseData;
      try {
        const response = await apiClient.post<SessionResponseData>("/auth/login", {
          username: credentials.username,
          password: credentials.password,
          facility_id: credentials.facility_id,
        });
        if (!response.data) throw new AuthError("Empty response from server.", "UNKNOWN");
        data = response.data;
      } catch (error) {
        throw error instanceof AuthError ? error : toAuthError(error);
      }
      // A different user (role/permissions/tenant) may sign in on top of a
      // previous session's cache - start clean.
      queryClient.clear();
      lastActivityRef.current = Date.now();
      return applySession(data);
    },
    [queryClient, applySession]
  );

  const switchFacility = React.useCallback(
    async (facilityId: string) => {
      if (facilityId === facility?.id) return;
      try {
        const response = await apiClient.post<SessionResponseData>("/auth/switch-facility", {
          facility_id: facilityId,
        });
        if (!response.data) return;
        queryClient.clear(); // facility-scoped data must not carry over
        applySession(response.data);
        toast({ title: "Facility switched", description: response.data.facility.name, variant: "info" });
        router.push("/dashboard");
      } catch (error) {
        toast({
          title: "Could not switch facility",
          description: (error as ApiError)?.message || "Please try again.",
          variant: "destructive",
        });
      }
    },
    [facility?.id, queryClient, applySession, toast, router]
  );

  const changePassword = React.useCallback(async (input: ChangePasswordInput) => {
    if (input.new_password !== input.confirm_password) {
      throw new Error("New password and confirmation do not match.");
    }

    try {
      await apiClient.post("/auth/change-password", {
        current_password: input.current_password,
        new_password: input.new_password,
      });
    } catch (error) {
      const apiError = error as ApiError;
      throw new Error(apiError?.message || "Unable to change password.");
    }
  }, []);

  const hasPermission = React.useCallback(
    (permission: string) => {
      if (!user) return false;
      return user.permissions.includes(permission);
    },
    [user]
  );

  const extendSession = React.useCallback(() => {
    lastActivityRef.current = Date.now();
    setSessionTimeout({ isWarningVisible: false, secondsRemaining: IDLE_WARNING_MS / 1000 });
  }, []);

  // Inactivity monitor: warn 60s before the 15-minute idle limit, then auto sign out.
  React.useEffect(() => {
    if (!user) return;

    const handleActivity = () => {
      if (!sessionTimeout.isWarningVisible) {
        lastActivityRef.current = Date.now();
      }
    };
    ACTIVITY_EVENTS.forEach((event) => window.addEventListener(event, handleActivity));

    const interval = setInterval(() => {
      const idleFor = Date.now() - lastActivityRef.current;
      const remainingUntilWarning = IDLE_LIMIT_MS - IDLE_WARNING_MS - idleFor;

      if (remainingUntilWarning <= 0) {
        const secondsRemaining = Math.max(0, Math.ceil((IDLE_LIMIT_MS - idleFor) / 1000));
        if (secondsRemaining <= 0) {
          void logout("idle");
        } else {
          setSessionTimeout({ isWarningVisible: true, secondsRemaining });
        }
      }
    }, 1000);

    return () => {
      ACTIVITY_EVENTS.forEach((event) => window.removeEventListener(event, handleActivity));
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, sessionTimeout.isWarningVisible]);

  const value: InternalAuthContextType = {
    user,
    tenant,
    facility,
    availableFacilities: facilities,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    switchFacility,
    changePassword,
    hasPermission,
    sessionTimeout,
    extendSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): InternalAuthContextType {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error("useAuthContext must be used within an <AuthProvider />");
  }
  return context;
}
