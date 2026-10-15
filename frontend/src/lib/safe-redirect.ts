/**
 * P9-F01: post-login redirects come from a query string, so they are
 * attacker-controlled. Only same-origin absolute paths are allowed; anything
 * else (`//evil.com`, `https://…`, `javascript:`, backslash tricks) falls
 * back to `fallback`.
 */
export function safeRedirectPath(target: string | null | undefined, fallback = "/"): string {
  if (!target || !target.startsWith("/")) return fallback;
  if (target.startsWith("//") || target.includes("\\")) return fallback;
  // Control characters (tab/newline) are stripped by browsers before parsing,
  // which can turn "/\t/evil.com" into "//evil.com".
  if (/[\u0000-\u001f\u007f]/.test(target)) return fallback;
  return target;
}
