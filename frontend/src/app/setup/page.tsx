"use client";

import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { TenantSetupWizard } from "@/components/setup/tenant-setup-wizard";

// Reachable only with `tenants.manage` (route policy in lib/route-access.ts); the
// API additionally requires the SUPER_ADMIN role, so this page is a convenience
// for platform operators, never the security boundary.
export default function HospitalSetupPage() {
  return (
    <AppShell>
      <div className="mx-auto max-w-5xl space-y-6">
        <PageHeader
          title="Hospital setup"
          description="Create a new hospital or clinic organisation, its first facility and its administrator."
        />
        <TenantSetupWizard />
      </div>
    </AppShell>
  );
}
