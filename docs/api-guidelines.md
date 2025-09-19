# API Guidelines

- All protected requests must include the `Authorization: Bearer` header and the tenant header defined by `TENANT_HEADER`.
- Responses use snake_case fields and wrap errors using the application error format `{code, message, details?}`.
- Pagination uses `limit` and `cursor` query parameters; cursors are opaque UUID strings.
- Optimistic concurrency uses the `version` field; clients provide the current version on updates.
- OpenAPI schema is exported to `docs/openapi/schema.json` via `make export-openapi`.

- DELETE operations mark resources with `deleted_at` and omit them from standard queries.
- Auth endpoints: POST /api/v1/auth/login (returns bearer token), POST /api/v1/auth/register (ADMIN only), POST /api/v1/auth/change-password (self).
