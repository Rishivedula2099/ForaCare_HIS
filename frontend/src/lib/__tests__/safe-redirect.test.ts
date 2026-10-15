import { describe, expect, it } from "vitest";
import { safeRedirectPath } from "../safe-redirect";

describe("safeRedirectPath", () => {
  it("allows same-origin paths", () => {
    expect(safeRedirectPath("/billing/invoices/1?x=2")).toBe("/billing/invoices/1?x=2");
  });

  it.each([
    "//evil.com",
    "https://evil.com",
    "javascript:alert(1)",
    "/" + String.fromCharCode(92) + "evil.com",
    "/" + String.fromCharCode(9) + "/evil.com",
    "evil.com",
    "",
    null,
    undefined,
  ])("rejects %j", (value) => {
    expect(safeRedirectPath(value as string | null | undefined)).toBe("/");
  });
});
