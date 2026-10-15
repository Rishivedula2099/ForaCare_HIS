import { describe, expect, it } from "vitest";
import { decideRoute, isPublicRoute, ROUTE_POLICIES } from "../route-access";

const as = (...codes: string[]) => (code: string) => codes.includes(code);
const prod = { demoEnabled: false };
const dev = { demoEnabled: true };

describe("route access policy", () => {
  it("treats auth pages as public and everything else as private", () => {
    expect(isPublicRoute("/login")).toBe(true);
    expect(isPublicRoute("/forbidden")).toBe(true);
    expect(isPublicRoute("/patients")).toBe(false);
    expect(isPublicRoute("/loginx")).toBe(false);
    expect(isPublicRoute("/")).toBe(false);
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
