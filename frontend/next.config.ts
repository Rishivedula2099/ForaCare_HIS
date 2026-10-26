import type { NextConfig } from "next";
import path from "path";

const isDev = process.env.NODE_ENV !== "production";

function origin(url: string | undefined): string | null {
  try {
    return url ? new URL(url).origin : null;
  } catch {
    return null;
  }
}

// P9-F01: CSP. The API origin must be allowed for XHR and the OPD queue
// WebSocket; documents render as blob: PDFs inside an iframe. Next's inline
// bootstrap scripts need 'unsafe-inline' until nonce-based CSP is adopted;
// 'unsafe-eval' is dev-only (React refresh).
const apiOrigin = origin(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");
const connectSrc = ["'self'"];
if (apiOrigin) connectSrc.push(apiOrigin, apiOrigin.replace(/^http/, "ws"));

const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  `img-src 'self' data: blob:${apiOrigin ? ` ${apiOrigin}` : ""}`,
  "font-src 'self' data:",
  `connect-src ${connectSrc.join(" ")}`,
  "frame-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "geolocation=(), microphone=(), camera=()" },
  ...(isDev
    ? []
    : [{ key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" }]),
];

const nextConfig: NextConfig = {
  // Produces a minimal self-contained server bundle (node_modules pruned to
  // only what's traced as actually used) so the Docker image doesn't need a
  // full `npm install` at runtime.
  output: "standalone",
  poweredByHeader: false,
  turbopack: {
    root: path.resolve(__dirname),
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
