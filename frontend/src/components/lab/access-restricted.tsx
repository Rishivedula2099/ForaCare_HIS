import { ShieldAlert } from "lucide-react";

/**
 * Module-level access guard for the Laboratory pages, gated on `lab.view`
 * (mirrors `billing.view` - see
 * frontend/src/components/billing/access-restricted.tsx and
 * backend/app/modules/rbac/constants.py). Rendered inline by the page
 * itself, not via the API client's generic 403->/forbidden redirect.
 */
export function LabAccessRestricted() {
  return (
    <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
      <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
      <div>
        <p className="font-semibold">You don&apos;t have permission to view the Laboratory module.</p>
        <p className="text-amber-700 mt-0.5">Contact a Hospital Admin if you believe you should have access.</p>
      </div>
    </div>
  );
}
