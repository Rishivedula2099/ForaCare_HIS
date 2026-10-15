import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// P10-B01 guards: the browser bundle must contain no shipped credentials, no
// client-side authentication bypass, and no fixed tenant/facility identifiers.
const root = path.resolve(__dirname, "../..");

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) return name === "__tests__" ? [] : sourceFiles(full);
    return /\.(ts|tsx)$/.test(name) ? [full] : [];
  });
}

const files = sourceFiles(root).map((file) => ({ file, text: readFileSync(file, "utf8") }));
const offenders = (re: RegExp) => files.filter(({ text }) => re.test(text)).map(({ file }) => path.relative(root, file));

describe("no prototype-only identity paths in the frontend", () => {
  it("ships no demo credentials", () => {
    expect(offenders(/Demo@123|DEMO_PRESETS|MOCK_STAFF_DIRECTORY/)).toEqual([]);
  });

  it("has no mock login / offline auth fallback or demo-login switch", () => {
    expect(offenders(/mockLogin|auth-mock|isUsingMockAuth|MOCK_AUTH_ENABLED|ENABLE_DEMO_LOGIN/)).toEqual([]);
  });

  it("embeds no fixed tenant or facility ids", () => {
    expect(offenders(/(11111111-1111|22222222-2222|33333333-3333|44444444-4444)-/)).toEqual([]);
  });

  it("keeps no client-side patient store or simulated ABDM verification", () => {
    expect(offenders(/patient-store|simulateAbdmOtpVerification|foracare_patients_store/)).toEqual([]);
  });

  it("decides authorization from permissions, not role-name lists", () => {
    expect(offenders(/\bhasRole\b|allowedRoles/)).toEqual([]);
  });

  it("does not hard-code one hospital's name into screens", () => {
    expect(
      offenders(/ForaCare City Hospital|ForaCare Health Network|ForaCare South Clinic|ForaCare Metro/).filter(
        (file) => !file.replace(/\\/g, "/").startsWith("app/design-system")
      )
    ).toEqual([]);
  });
});
