"use client";

import * as React from "react";
import { IS_DEV_BUILD } from "@/lib/constants";
import { decideRoute } from "@/lib/route-access";
import { useAuth } from "@/hooks/use-auth";

/** `canAccess(path)` for the signed-in user, from their effective permissions. */
export function useRouteAccess() {
  const { hasPermission } = useAuth();
  return React.useCallback(
    (pathname: string) =>
      decideRoute(pathname, hasPermission, { devToolsEnabled: IS_DEV_BUILD }) === "allow",
    [hasPermission]
  );
}
