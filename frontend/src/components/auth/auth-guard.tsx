"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { PageLoadingState } from "@/components/states/loading-state";

/**
 * Requires a signed-in user. Authorization is by permission and is enforced
 * centrally by `RouteAccessGate` (lib/route-access.ts) plus the API itself -
 * there are no per-page role lists.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  React.useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace(`/login?redirect=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, isAuthenticated, router, pathname]);

  if (isLoading || !isAuthenticated) {
    return <PageLoadingState label="Verifying session..." />;
  }

  return <>{children}</>;
}
