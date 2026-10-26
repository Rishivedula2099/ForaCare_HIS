import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// P9-F01 guard: raw-HTML sinks must not creep back in without review.
const SINKS = /dangerouslySetInnerHTML|\.innerHTML\s*=|\.outerHTML\s*=|insertAdjacentHTML|document\.write\(|\beval\(|new Function\(/;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) return name === "__tests__" ? [] : sourceFiles(full);
    return /\.(ts|tsx)$/.test(name) ? [full] : [];
  });
}

describe("frontend source", () => {
  it("contains no raw-HTML or dynamic-code sinks", () => {
    const root = path.resolve(__dirname, "../..");
    const offenders = sourceFiles(root).filter((file) => SINKS.test(readFileSync(file, "utf8")));
    expect(offenders).toEqual([]);
  });
});
