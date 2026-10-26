/**
 * P9-F03: central route -> permission policy.
 *
 * Hiding a sidebar link is not access control: a user can type any URL. Every
 * private route is checked here (by `RouteAccessGate`, mounted in the root
 * layout so print/report pages without an AppShell are covered too). The API
 * remains the real enforcement point - this keeps a role from landing on a
 * page it cannot use, and from firing queries that are certain to 403.
 *
 * Permission codes must exist in the backend catalog
 * (backend/app/modules/rbac/constants.py); a backend test enforces that.
 */

import { MAIN_NAV_ITEMS, NavItem } from "@/lib/constants";
import { safeRedirectPath } from "@/lib/safe-redirect";

/**
 * Routes reachable without a session. `/` is the public landing page and is
 * matched exactly (see `isPublicRoute`) so it doesn't make everything public.
 * `/verify-account` is NOT here: it is the signed-in email/phone OTP screen;
 * emailed activation links land on `/activate-account`.
 */
export const PUBLIC_ROUTES = [
  "/login",
  "/forgot-password",
  "/reset-password",
  "/activate-account",
  "/request-onboarding",
  "/unauthorized",
  "/forbidden",
] as const;

export interface RoutePolicy {
  /** Matches the path itself and everything beneath it. */
  prefix: string;
  /** User needs ANY of these permissions. Omit for "any signed-in user". */
  anyOf?: string[];
  /** Only reachable in non-production builds (developer tooling). */
  devOnly?: boolean;
}

/** First match wins - keep more specific prefixes above general ones. */
export const ROUTE_POLICIES: RoutePolicy[] = [
  { prefix: "/design-system", devOnly: true },

  { prefix: "/patients/new", anyOf: ["patients.manage"] },
  { prefix: "/patients", anyOf: ["patients.view"] },

  { prefix: "/opd/consultation", anyOf: ["consultations.view"] },
  { prefix: "/opd", anyOf: ["opd.view"] },

  { prefix: "/ipd/allocate", anyOf: ["ipd.manage_beds"] },
  { prefix: "/ipd", anyOf: ["ipd.view"] },

  { prefix: "/billing", anyOf: ["billing.view"] },
  { prefix: "/laboratory", anyOf: ["lab.view"] },

  { prefix: "/departments", anyOf: ["departments.view"] },
  { prefix: "/doctors", anyOf: ["doctors.view"] },

  { prefix: "/documents/templates", anyOf: ["documents.manage_templates"] },
  // Printing: the backend checks the per-document-type permission.
  { prefix: "/documents", anyOf: ["documents.print", "documents.manage_templates"] },

  // Platform operators (SUPER_ADMIN) create hospitals here; the API re-checks the role.
  { prefix: "/setup", anyOf: ["tenants.manage"] },
  { prefix: "/roles", anyOf: ["roles.view"] },
  { prefix: "/audit", anyOf: ["audit.view_logs"] },
  { prefix: "/settings", anyOf: ["facilities.manage", "users.manage"] },
];

function matches(pathname: string, prefix: string): boolean {
  return pathname === prefix || pathname.startsWith(prefix + "/");
}

export function isPublicRoute(pathname: string): boolean {
  return pathname === "/" || PUBLIC_ROUTES.some((route) => matches(pathname, route));
}

export type RouteDecision = "allow" | "forbidden";

/**
 * Decides whether a signed-in user may open `pathname`, from their effective
 * permissions (`hasPermission`) alone - never from a role name.
 */
export function decideRoute(
  pathname: string,
  hasPermission: (code: string) => boolean,
  options: { devToolsEnabled: boolean }
): RouteDecision {
  const policy = ROUTE_POLICIES.find((p) => matches(pathname, p.prefix));
  if (!policy) return "allow";
  if (policy.devOnly && !options.devToolsEnabled) return "forbidden";
  if (policy.anyOf && !policy.anyOf.some(hasPermission)) return "forbidden";
  return "allow";
}

/** Module routes (dashboard excluded) the user can open - their working set. */
export function accessibleModules(
  hasPermission: (code: string) => boolean,
  options: { devToolsEnabled: boolean }
): NavItem[] {
  return MAIN_NAV_ITEMS.filter(
    (item) => item.href !== "/dashboard" && decideRoute(item.href, hasPermission, options) === "allow"
  );
}

/**
 * Where to send a user right after sign-in.
 *  1. A requested deep link, if it is same-origin, private, and permitted.
 *  2. `/dashboard` (the permission-driven home) if they can open any module.
 *  3. `/forbidden` if their role grants no module at all - an empty
 *     dashboard would read as a broken app rather than a missing assignment.
 */
export function resolvePostLoginPath(
  requested: string | null | undefined,
  hasPermission: (code: string) => boolean,
  options: { devToolsEnabled: boolean }
): string {
  const target = safeRedirectPath(requested, "");
  if (target && !isPublicRoute(target) && decideRoute(target, hasPermission, options) === "allow") {
    return target;
  }
  return accessibleModules(hasPermission, options).length > 0 ? "/dashboard" : "/forbidden";
}
