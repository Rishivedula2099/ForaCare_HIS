import { describe, expect, it } from "vitest";
import {
  accessibleModules,
  decideRoute,
  isPublicRoute,
  resolvePostLoginPath,
  ROUTE_POLICIES,
} from "../route-access";

const as = (...codes: string[]) => (code: string) => codes.includes(code);
const prod = { devToolsEnabled: false };
const dev = { devToolsEnabled: true };

describe("route access policy", () => {
  it("treats auth pages as public and everything else as private", () => {
    expect(isPublicRoute("/login")).toBe(true);
    expect(isPublicRoute("/forbidden")).toBe(true);
    expect(isPublicRoute("/patients")).toBe(false);
    expect(isPublicRoute("/loginx")).toBe(false);
  });

  it("makes only the landing page and onboarding enquiry public, not everything under /", () => {
    expect(isPublicRoute("/")).toBe(true);
    expect(isPublicRoute("/request-onboarding")).toBe(true);
    expect(isPublicRoute("/activate-account")).toBe(true);
    expect(isPublicRoute("/dashboard")).toBe(false);
    expect(isPublicRoute("/patients")).toBe(false);
    // The signed-in email/phone OTP screen stays private; emailed links use /activate-account.
    expect(isPublicRoute("/verify-account")).toBe(false);
  });

  it("denies a role without the module permission, even on a typed URL", () => {
    expect(decideRoute("/billing/invoices/123", as("patients.view"), prod)).toBe("forbidden");
    expect(decideRoute("/laboratory/orders/9/report", as("billing.view"), prod)).toBe("forbidden");
    expect(decideRoute("/ipd/admissions/1/print/labels", as("patients.view"), prod)).toBe("forbidden");
    expect(decideRoute("/documents/templates", as("documents.print"), prod)).toBe("forbidden");
  });

  it("allows the right permission and nested paths", () => {
    expect(decideRoute("/billing", as("billing.view"), prod)).toBe("allow");
    expect(decideRoute("/billing/invoices/receipts/5", as("billing.view"), prod)).toBe("allow");
    expect(decideRoute("/opd/consultation/7", as("consultations.view"), prod)).toBe("allow");
  });

  it("applies the most specific policy first", () => {
    // /patients/new needs manage, not just view.
    expect(decideRoute("/patients/new", as("patients.view"), prod)).toBe("forbidden");
    expect(decideRoute("/patients/new", as("patients.manage"), prod)).toBe("allow");
    expect(decideRoute("/ipd/allocate", as("ipd.view"), prod)).toBe("forbidden");
    expect(decideRoute("/ipd/wards", as("ipd.view"), prod)).toBe("allow");
  });

  it("does not match on a shared string prefix", () => {
    // "/billingfoo" is not under "/billing".
    expect(decideRoute("/billingfoo", as(), prod)).toBe("allow");
  });

  it("keeps the design-system page out of production", () => {
    expect(decideRoute("/design-system", as(), prod)).toBe("forbidden");
    expect(decideRoute("/design-system", as(), dev)).toBe("allow");
  });

  it("lets any signed-in user reach the dashboard and home", () => {
    expect(decideRoute("/", as(), prod)).toBe("allow");
    expect(decideRoute("/dashboard", as(), prod)).toBe("allow");
  });

  it("has no duplicate prefixes (first match would shadow the later one)", () => {
    const prefixes = ROUTE_POLICIES.map((p) => p.prefix);
    expect(new Set(prefixes).size).toBe(prefixes.length);
  });
});

describe("post-login routing by effective permissions", () => {
  it("sends users with module access to the permission-driven dashboard", () => {
    expect(resolvePostLoginPath(null, as("lab.view"), prod)).toBe("/dashboard");
    expect(resolvePostLoginPath(undefined, as("billing.view", "patients.view"), prod)).toBe("/dashboard");
  });

  it("honours a permitted deep link", () => {
    expect(resolvePostLoginPath("/billing/invoices/9", as("billing.view"), prod)).toBe("/billing/invoices/9");
  });

  it("ignores a deep link the user cannot open", () => {
    expect(resolvePostLoginPath("/billing", as("lab.view"), prod)).toBe("/dashboard");
  });

  it("ignores unsafe, public or landing redirects", () => {
    const user = as("lab.view");
    expect(resolvePostLoginPath("//evil.example", user, prod)).toBe("/dashboard");
    expect(resolvePostLoginPath("https://evil.example", user, prod)).toBe("/dashboard");
    expect(resolvePostLoginPath("/", user, prod)).toBe("/dashboard");
    expect(resolvePostLoginPath("/login", user, prod)).toBe("/dashboard");
  });

  it("sends a user whose role grants no module to the access-restricted page", () => {
    expect(resolvePostLoginPath(null, as(), prod)).toBe("/forbidden");
    expect(resolvePostLoginPath(null, as("some.unknown.permission"), prod)).toBe("/forbidden");
  });

  it("lists only the modules the permissions admit, never the dashboard itself", () => {
    const hrefs = accessibleModules(as("patients.view", "lab.view"), prod).map((m) => m.href);
    expect(hrefs).toEqual(["/patients", "/laboratory"]);
    expect(accessibleModules(as(), prod)).toEqual([]);
  });

  it("does not depend on role names", () => {
    // A custom role is just a set of permissions.
    expect(accessibleModules(as("documents.print"), prod).map((m) => m.href)).toEqual(["/documents"]);
  });
});

describe("hospital setup route", () => {
  it("is limited to holders of tenants.manage", () => {
    expect(decideRoute("/setup", as("roles.view", "users.manage", "facilities.manage"), prod)).toBe("forbidden");
    expect(decideRoute("/setup", as("tenants.manage"), prod)).toBe("allow");
  });

  it("is not public", () => {
    expect(isPublicRoute("/setup")).toBe(false);
  });
});
