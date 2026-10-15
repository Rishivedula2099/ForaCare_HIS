import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// P9-F02 guards: auth tokens live only in HttpOnly cookies the browser
// manages; the frontend must never read, store, log or URL-embed them.
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

describe("token exposure", () => {
  it("never touches document.cookie", () => {
    expect(offenders(/document\.cookie/)).toEqual([]);
  });

  it("never stores access/refresh/jwt tokens in web storage", () => {
    expect(
      offenders(/(local|session)Storage\.setItem\(\s*[^)]*(token|jwt|bearer|secret)/i)
    ).toEqual([]);
  });

  it("never logs tokens or Authorization headers", () => {
    expect(offenders(/console\.\w+\([^)]*(access_?token|refresh_?token|jwt|authorization)/i)).toEqual([]);
  });

  it("never puts access/refresh tokens in URLs", () => {
    expect(offenders(/[?&](access_?token|refresh_?token|jwt)=/i)).toEqual([]);
  });

  it("exposes no secrets through NEXT_PUBLIC_ variables", () => {
    const names = files.flatMap(({ text }) => text.match(/NEXT_PUBLIC_[A-Z0-9_]+/g) ?? []);
    const bad = names.filter((name) => /SECRET|PASSWORD|PRIVATE|TOKEN|CREDENTIAL|KEY/.test(name));
    expect(bad).toEqual([]);
  });
});
