"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import { findFacilityById, MOCK_FACILITIES, mockLogin } from "@/lib/auth-mock";
import { UserRole } from "@/lib/constants";
import { ApiError } from "@/types/api";
import {
  AuthContextType,
  AuthSession,
  AuthTokens,
  AuthUser,
  ChangePasswordInput,
  Facility,
  LoginCredentials,
  ROLE_METADATA_MAP,
  Tenant,
} from "@/types/auth";
import { useToast } from "@/hooks/use-toast";

const STORAGE_KEYS = {
  accessToken: "foracare_access_token",
  refreshToken: "foracare_refresh_token",
  tenantId: "foracare_tenant_id",
  facilityId: "foracare_facility_id",
  session: "foracare_session",
} as const;

const IDLE_LIMIT_MS = 15 * 60 * 1000;
const IDLE_WARNING_MS = 60 * 1000;
const ACTIVITY_EVENTS: (keyof WindowEventMap)[] = ["mousemove", "mousedown", "keydown", "scroll", "touchstart"];

interface StoredSession {
  user: AuthUser;
  tenant: Tenant;
  facility: Facility;
}

interface LoginResponseData extends StoredSession {
  tokens: AuthTokens;
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

function persistSession(session: AuthSession) {
  localStorage.setItem(STORAGE_KEYS.accessToken, session.tokens.access_token);
  localStorage.setItem(STORAGE_KEYS.refreshToken, session.tokens.refresh_token);
  localStorage.setItem(STORAGE_KEYS.tenantId, session.tenant.id);
  localStorage.setItem(STORAGE_KEYS.facilityId, session.facility.id);
  localStorage.setItem(
    STORAGE_KEYS.session,
    JSON.stringify({ user: session.user, tenant: session.tenant, facility: session.facility })
  );
}

function clearSession() {
  Object.values(STORAGE_KEYS).forEach((key) => localStorage.removeItem(key));
}

function readStoredSession(): StoredSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.session);
    if (!raw) return null;
    return JSON.parse(raw) as StoredSession;
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

  // Hydrate from localStorage on mount so a page refresh doesn't log the
  // user out. This can only run client-side (localStorage isn't available
  // during SSR/static generation), so a one-time effect - not a lazy
  // useState initializer - is the correct, SSR-safe way to read it.
  /* eslint-disable react-hooks/set-state-in-effect */
  React.useEffect(() => {
    lastActivityRef.current = Date.now();
    const stored = readStoredSession();
    const hasToken = !!localStorage.getItem(STORAGE_KEYS.accessToken);

    if (stored && hasToken) {
      setUser(stored.user);
      setTenant(stored.tenant);
      setFacility(stored.facility);
      const refreshToken = localStorage.getItem(STORAGE_KEYS.refreshToken);
      setIsUsingMockAuth(!!refreshToken?.startsWith("mock_"));
    }
    setIsLoading(false);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  React.useEffect(() => {
    isAuthenticatedRef.current = !!user;
  }, [user]);

  const logout = React.useCallback(async () => {
    const refreshToken = localStorage.getItem(STORAGE_KEYS.refreshToken);
    if (refreshToken && !refreshToken.startsWith("mock_")) {
      try {
        await apiClient.post("/auth/logout", { refresh_token: refreshToken });
      } catch {
        // best-effort - still clear local state below even if the server call fails.
      }
    }
    clearSession();
    setUser(null);
    setTenant(null);
    setFacility(null);
    setIsUsingMockAuth(false);
    setSessionTimeout({ isWarningVisible: false, secondsRemaining: IDLE_WARNING_MS / 1000 });
    router.push("/login");
  }, [router]);

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
      session = response.data;
    } catch (error) {
      if (!isNetworkError(error)) {
        const apiError = error as ApiError;
        throw new Error(apiError?.message || "Invalid username or password.");
      }
      // Backend unreachable - fall back to mock auth so the UI stays usable.
      session = await mockLogin(credentials.username, credentials.password);
      usedMock = true;
    }

    persistSession(session);
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
      localStorage.setItem(STORAGE_KEYS.facilityId, target.id);
      const stored = readStoredSession();
      if (stored) {
        localStorage.setItem(
          STORAGE_KEYS.session,
          JSON.stringify({ ...stored, facility: target })
        );
      }
      toast({ title: "Facility switched", description: target.name, variant: "info" });
    },
    [toast]
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
      const metadata = ROLE_METADATA_MAP[user.role];
      return metadata.keyPermissions.some((p) => p.toLowerCase().includes(permission.toLowerCase()));
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
