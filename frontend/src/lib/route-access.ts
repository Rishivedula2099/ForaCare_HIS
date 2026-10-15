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

/** Routes reachable without a session. */
export const PUBLIC_ROUTES = [
  "/login",
  "/forgot-password",
  "/reset-password",
  "/verify-account",
  "/unauthorized",
  "/forbidden",
] as const;

export interface RoutePolicy {
  /** Matches the path itself and everything beneath it. */
  prefix: string;
  /** User needs ANY of these permissions. Omit for "any signed-in user". */
  anyOf?: string[];
  /** Only reachable in non-production / demo builds. */
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

  { prefix: "/roles", anyOf: ["roles.view"] },
  { prefix: "/audit", anyOf: ["audit.view_logs"] },
  { prefix: "/settings", anyOf: ["facilities.manage", "users.manage"] },
];

function matches(pathname: string, prefix: string): boolean {
  return pathname === prefix || pathname.startsWith(prefix + "/");
}

export function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some((route) => matches(pathname, route));
}

export type RouteDecision = "allow" | "forbidden";

/**
 * Decides whether a signed-in user may open `pathname`.
 * `hasPermission` is injected so the offline mock session (whose permission
 * list lags the backend catalog) can opt out of permission checks.
 */
export function decideRoute(
  pathname: string,
  hasPermission: (code: string) => boolean,
  options: { demoEnabled: boolean }
): RouteDecision {
  const policy = ROUTE_POLICIES.find((p) => matches(pathname, p.prefix));
  if (!policy) return "allow";
  if (policy.devOnly && !options.demoEnabled) return "forbidden";
  if (policy.anyOf && !policy.anyOf.some(hasPermission)) return "forbidden";
  return "allow";
}
