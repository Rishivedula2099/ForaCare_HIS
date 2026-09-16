"use client";

import Link from "next/link";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { useAuth } from "@/hooks/use-auth";
import { RoleDashboard } from "@/components/dashboard/role-dashboard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ROLE_METADATA_MAP } from "@/types/auth";

// Authorization is by permission, not by URL: this single /dashboard route
// resolves its content from the caller's role/permissions (S1-F02) rather
// than the app exposing a separate page per role.
export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardContent />
    </AuthGuard>
  );
}

function DashboardContent() {
  const { user, facility } = useAuth();

  if (!user) return null;

  const metadata = ROLE_METADATA_MAP[user.role];

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Welcome back, {user.full_name.split(" ")[0]}
              </h1>
              <Badge className={metadata.badgeClassName}>{metadata.label}</Badge>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {facility?.name ?? "No facility context"} - {metadata.description}
            </p>
          </div>
          <Link href="/">
            <Button variant="outline" size="sm">
              Full Operations View
            </Button>
          </Link>
        </div>

        <RoleDashboard role={user.role} />
      </div>
    </AppShell>
  );
}
