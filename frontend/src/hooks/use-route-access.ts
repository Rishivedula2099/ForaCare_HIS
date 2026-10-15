"use client";

import * as React from "react";
import { MOCK_AUTH_ENABLED } from "@/lib/constants";
import { decideRoute } from "@/lib/route-access";
import { useAuth } from "@/hooks/use-auth";

/**
 * `canAccess(path)` for the signed-in user. The offline mock session carries
 * a permission list that lags the backend catalog, so it is exempt from
 * permission checks (it only exists in non-production builds).
 */
export function useRouteAccess() {
  const { hasPermission, isUsingMockAuth } = useAuth();
  return React.useCallback(
    (pathname: string) =>
      decideRoute(pathname, isUsingMockAuth ? () => true : hasPermission, {
        demoEnabled: MOCK_AUTH_ENABLED,
      }) === "allow",
    [hasPermission, isUsingMockAuth]
  );
}
