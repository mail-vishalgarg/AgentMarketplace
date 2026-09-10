# Security Rules

1. **No secrets in code.** All credentials, API keys, and tokens live in environment variables only. Never hard-code them, never `print()` them, never include them in logs.

2. **Config from environment only.** Use `pydantic-settings` (`BaseSettings`) to read config. If a required var is missing, the app fails at startup with a clear message — not silently at runtime.

3. **Hash API keys, never store raw.** User-supplied API keys are hashed (SHA-256 keyed with a server secret) before storage. The raw value is discarded immediately after hashing.

4. **Validate all external input.** Every value crossing a trust boundary (HTTP request body, query param, MCP tool response, webhook payload) goes through a Pydantic model before touching business logic. Reject unknowns with `model_config = ConfigDict(extra="forbid")`.

5. **Credentials are write-only.** Once stored (Fernet/KMS encrypted), credentials are never returned in API responses. Endpoints return a masked representation only.

6. **No cross-tenant data leakage.** Every DB query against a tenant-scoped table must include the current tenant filter. Supabase RLS is the safety net, not the primary control.
