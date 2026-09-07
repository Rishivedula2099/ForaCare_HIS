"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { UserRole } from "@/lib/constants";
import { PageLoadingState } from "@/components/states/loading-state";

interface AuthGuardProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export function AuthGuard({ children, allowedRoles }: AuthGuardProps) {
  const { isAuthenticated, isLoading, hasRole } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  React.useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated) {
      router.replace(`/login?redirect=${encodeURIComponent(pathname)}`);
      return;
    }

    if (!hasRole(allowedRoles)) {
      router.replace("/forbidden");
    }
  }, [isLoading, isAuthenticated, hasRole, allowedRoles, router, pathname]);

  if (isLoading || !isAuthenticated || !hasRole(allowedRoles)) {
    return <PageLoadingState label="Verifying session..." />;
  }

  return <>{children}</>;
}
