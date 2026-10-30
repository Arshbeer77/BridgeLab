# Future local automation boundary — design only

v0.3 opens no network listener and adds no Hermes, n8n or MCP integration.

Before implementing an API:
- Bind only to loopback; no LAN exposure by default. Check Host and Origin, require authentication for every request, and reject browser cross-origin access.
- Generate a per-installation random token, store using Windows credential protection, support rotation/revocation, and never log it.
- Pair each client with user-approved capabilities and an explicitly selected device. A trusted client still needs per-action policy enforcement.
- Begin with read-only status and diagnostics. Then add explicit file-send/link-open requests with UI confirmation and narrowly scoped path/URL validation.
- No arbitrary adb command, shell, app scripting, unrestricted filesystem read, background screen capture or unattended input endpoint.
- Serialize device jobs, use bounded timeouts, rate limits and cancellation, and idempotency keys. Do not blindly replay transfers or input after reconnect.
- Audit client identity, approved capability and outcome without private content. Provide a visible master disable switch and revoke all sessions when disabled.
- Isolate the command runner behind a service boundary; adapters for Hermes, n8n and MCP call the same authorization layer.

Threat review and Windows authentication/integration tests are release gates before enabling any listener. This document is not a claim that these safeguards have been implemented.
