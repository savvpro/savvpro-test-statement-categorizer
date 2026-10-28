"""Security response headers, shared by the middleware and the unhandled-500 handler."""

STATIC_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}
CSP = "default-src 'self'; frame-ancestors 'none'"


def security_headers(*, relaxed: bool = False) -> dict[str, str]:
    headers = dict(STATIC_SECURITY_HEADERS)
    if not relaxed:
        headers["Content-Security-Policy"] = CSP
    return headers
