import type { NextConfig } from "next";

const api = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

// CSP note: Next.js emits inline bootstrap scripts, so 'unsafe-inline' stays for script-src. Dropping
// it needs a per-request nonce from middleware, which forces every page to render dynamically; the app
// has no HTML injection sink (React escapes all output), so this is an accepted trade-off.
// Everything else is locked down: no objects, no foreign base URI or form targets, no framing,
// and 'unsafe-eval' is development-only (React refresh).
const securityHeaders = [
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline'" + (process.env.NODE_ENV === "production" ? "" : " 'unsafe-eval'"),
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data:",
      "font-src 'self'",
      "connect-src 'self'",
      "object-src 'none'",
      "base-uri 'self'",
      "form-action 'self'",
      "frame-ancestors 'none'",
    ].join("; "),
  },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*` },
      { source: "/healthz", destination: `${api}/healthz` },
    ];
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
