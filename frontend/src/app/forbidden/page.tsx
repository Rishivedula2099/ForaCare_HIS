"use client";

import Link from "next/link";
import { ShieldOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/states/empty-state";
import { RoleBadge } from "@/components/common/role-badge";
import { useAuth } from "@/hooks/use-auth";

export default function ForbiddenPage() {
  const { user, facility } = useAuth();

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 p-6">
      <EmptyState
        icon={ShieldOff}
        title="Access restricted"
        description="Your role does not have permission to view this module. If you believe this is a mistake, contact your hospital administrator."
        action={
          <div className="flex flex-col items-center gap-4">
            {user && (
              <div className="flex flex-col items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-4 py-3">
                <p className="text-sm font-semibold text-slate-900">{user.full_name}</p>
                <RoleBadge role={user.role} />
                {facility && <p className="text-[11px] text-slate-500">{facility.name}</p>}
              </div>
            )}
            <div className="flex flex-wrap justify-center gap-2">
              <Button asChild size="sm">
                <Link href="/">Return to Dashboard</Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <a href="mailto:it-support@foracare-his.com">Contact IT Administrator</a>
              </Button>
            </div>
          </div>
        }
      />
    </div>
  );
}
