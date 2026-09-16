"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import { findFacilityById, MOCK_FACILITIES, mockLogin } from "@/lib/auth-mock";
import { UserRole } from "@/lib/constants";
import { ApiError } from "@/types/api";
import {
  adaptBackendUser,
  AuthContextType,
  AuthSession,
  AuthUser,
  BackendUserPayload,
  ChangePasswordInput,
  Facility,
  LoginCredentials,
  Tenant,
} from "@/types/auth";
import { useToast } from "@/hooks/use-toast";

// Real sessions are HttpOnly cookies set by the backend (S1-F01) - nothing
// about them is ever stored here. This key only caches the *offline demo*
// fallback session (see auth-mock.ts) in sessionStorage, since that mode
// has no real cookie to persist it and must survive a page refresh some
// other way. It holds user/tenant/facility only - never a token.
const MOCK_SESSION_STORAGE_KEY = "foracare_mock_session";

const IDLE_LIMIT_MS = 15 * 60 * 1000;
const IDLE_WARNING_MS = 60 * 1000;
const ACTIVITY_EVENTS: (keyof WindowEventMap)[] = ["mousemove", "mousedown", "keydown", "scroll", "touchstart"];

interface StoredMockSession {
  user: AuthUser;
  tenant: Tenant;
  facility: Facility;
}

interface MeResponseData {
  user: BackendUserPayload;
  tenant: Tenant;
  facility: Facility;
}

interface LoginResponseData {
  user: BackendUserPayload;
  tenant: Tenant;
  facility: Facility;
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

function persistMockSession(session: AuthSession) {
  sessionStorage.setItem(
    MOCK_SESSION_STORAGE_KEY,
    JSON.stringify({ user: session.user, tenant: session.tenant, facility: session.facility })
  );
}

function clearMockSession() {
  sessionStorage.removeItem(MOCK_SESSION_STORAGE_KEY);
}

function readStoredMockSession(): StoredMockSession | null {
  try {
    const raw = sessionStorage.getItem(MOCK_SESSION_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as StoredMockSession;
  } catch {
    return null;
  }
}

function isNetworkError(error: unknown): boolean {
  const apiError = error as Partial<ApiError>;
  return apiError?.code === "NETWORK_ERROR" || apiError?.code === "TIMEOUT";
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { toast } = useToast();

  const [user, setUser] = React.useState<AuthUser | null>(null);
  const [tenant, setTenant] = React.useState<Tenant | null>(null);
  const [facility, setFacility] = React.useState<Facility | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isUsingMockAuth, setIsUsingMockAuth] = React.useState(false);
  const [sessionTimeout, setSessionTimeout] = React.useState<SessionTimeoutState>({
    isWarningVisible: false,
    secondsRemaining: IDLE_WARNING_MS / 1000,
  });

  const lastActivityRef = React.useRef<number>(0);
  const isAuthenticatedRef = React.useRef(false);

  // Hydrate on mount. The real session lives in HttpOnly cookies the
  // browser already sent with this call - there is no client-side token to
  // read - so we simply ask the backend who (if anyone) is authenticated.
  // Only the offline mock fallback needs a client-side snapshot, since it
  // has no backend session to ask.
  React.useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      lastActivityRef.current = Date.now();
      try {
        const response = await apiClient.get<MeResponseData>("/auth/me");
        if (cancelled) return;
        if (response.data) {
          setUser(adaptBackendUser(response.data.user));
          setTenant(response.data.tenant);
          setFacility(response.data.facility);
          setIsUsingMockAuth(false);
          clearMockSession();
        }
      } catch (error) {
        if (cancelled) return;
        if (isNetworkError(error)) {
          const stored = readStoredMockSession();
          if (stored) {
            setUser(stored.user);
            setTenant(stored.tenant);
            setFacility(stored.facility);
            setIsUsingMockAuth(true);
          }
        }
        // A 401 simply means "not logged in" - nothing to restore.
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void hydrate();
    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => {
    isAuthenticatedRef.current = !!user;
  }, [user]);

  const logout = React.useCallback(async () => {
    if (!isUsingMockAuth) {
      try {
        await apiClient.post("/auth/logout");
      } catch {
        // best-effort - still clear local state below even if the server call fails.
      }
    }
    clearMockSession();
    setUser(null);
    setTenant(null);
    setFacility(null);
    setIsUsingMockAuth(false);
    setSessionTimeout({ isWarningVisible: false, secondsRemaining: IDLE_WARNING_MS / 1000 });
    router.push("/login");
  }, [isUsingMockAuth, router]);

  const login = React.useCallback(async (credentials: LoginCredentials) => {
    let session: AuthSession;
    let usedMock = false;

    try {
      const response = await apiClient.post<LoginResponseData>("/auth/login", {
        username: credentials.username,
        password: credentials.password,
        facility_id: credentials.facility_id,
      });
      if (!response.data) throw new Error("Empty login response from server.");
      session = {
        user: adaptBackendUser(response.data.user),
        tenant: response.data.tenant,
        facility: response.data.facility,
        session: { token_type: "bearer", expires_in: 15 * 60 },
      };
    } catch (error) {
      if (!isNetworkError(error)) {
        const apiError = error as ApiError;
        throw new Error(apiError?.message || "Invalid username or password.");
      }
      // Backend unreachable - fall back to mock auth so the UI stays usable.
      session = await mockLogin(credentials.username, credentials.password);
      usedMock = true;
    }

    if (usedMock) {
      persistMockSession(session);
    } else {
      clearMockSession();
    }
    setUser(session.user);
    setTenant(session.tenant);
    setFacility(session.facility);
    setIsUsingMockAuth(usedMock);
    lastActivityRef.current = Date.now();
  }, []);

  const switchFacility = React.useCallback(
    (facilityId: string) => {
      const target = findFacilityById(facilityId) ?? MOCK_FACILITIES.find((f) => f.id === facilityId);
      if (!target) return;
      setFacility(target);
      if (isUsingMockAuth) {
        const stored = readStoredMockSession();
        if (stored) {
          persistMockSession({
            user: stored.user,
            tenant: stored.tenant,
            facility: target,
            session: { token_type: "bearer", expires_in: 15 * 60 },
          });
        }
      }
      toast({ title: "Facility switched", description: target.name, variant: "info" });
    },
    [isUsingMockAuth, toast]
  );

  const changePassword = React.useCallback(
    async (input: ChangePasswordInput) => {
      if (input.new_password !== input.confirm_password) {
        throw new Error("New password and confirmation do not match.");
      }

      if (isUsingMockAuth) {
        await new Promise((resolve) => setTimeout(resolve, 400));
        return;
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
    },
    [isUsingMockAuth]
  );

  const hasRole = React.useCallback(
    (roles?: UserRole[]) => {
      if (!roles || roles.length === 0) return true;
      if (!user) return false;
      return roles.includes(user.role);
    },
    [user]
  );

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
          logout();
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
    availableFacilities: MOCK_FACILITIES,
    isAuthenticated: !!user,
    isLoading,
    isUsingMockAuth,
    login,
    logout,
    switchFacility,
    changePassword,
    hasRole,
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
