import { ShieldAlert } from "lucide-react";

/**
 * Module-level access guard for the Billing pages, gated on `billing.view`
 * (the single "can this role open the module at all" permission - see
 * `_FULL_BILLING_ACCESS`/`ROLE_PERMISSION_SEED` in
 * backend/app/modules/rbac/constants.py). Rendered inline by the page
 * itself rather than relying on the API client's generic 403->/forbidden
 * redirect, so a role without `billing.view` sees a clear, page-scoped
 * message instead of being yanked off the page - and so a role that *does*
 * have `billing.view` never risks tripping that redirect from some other
 * page-load query returning 403 for an unrelated reason.
 */
export function BillingAccessRestricted() {
  return (
    <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
      <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
      <div>
        <p className="font-semibold">You don&apos;t have permission to view the Billing module.</p>
        <p className="text-amber-700 mt-0.5">Contact a Hospital Admin if you believe you should have access.</p>
      </div>
    </div>
  );
}
