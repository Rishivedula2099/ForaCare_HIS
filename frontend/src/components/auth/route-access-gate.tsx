"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { useRouteAccess } from "@/hooks/use-route-access";
import { isPublicRoute } from "@/lib/route-access";
import { PageLoadingState } from "@/components/states/loading-state";

/**
 * Enforces the route policy for every page, including print/report pages
 * that render without an AppShell. Children are withheld until the session is
 * known and the route is permitted, so a forbidden page never mounts and
 * never fires its data queries.
 */
export function RouteAccessGate({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const canAccess = useRouteAccess();
  const router = useRouter();
  const pathname = usePathname();

  const isPublic = isPublicRoute(pathname);
  const allowed = isPublic || (isAuthenticated && canAccess(pathname));

  React.useEffect(() => {
    if (isPublic || isLoading) return;
    if (!isAuthenticated) {
      const search = typeof window === "undefined" ? "" : window.location.search;
      router.replace(`/login?redirect=${encodeURIComponent(pathname + search)}`);
    } else if (!canAccess(pathname)) {
      router.replace("/forbidden");
    }
  }, [isPublic, isLoading, isAuthenticated, canAccess, pathname, router]);

  if (isPublic) return <>{children}</>;
  if (isLoading || !allowed) return <PageLoadingState label="Verifying access..." />;
  return <>{children}</>;
}
