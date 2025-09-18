# API Guidelines

- All protected requests must include the `Authorization: Bearer` header and the tenant header defined by `TENANT_HEADER`.
- Responses use snake_case fields and wrap errors using the application error format `{code, message, details?}`.
- Pagination uses `limit` and `cursor` query parameters; cursors are opaque UUID strings.
- Optimistic concurrency uses the `version` field; clients provide the current version on updates.
- OpenAPI schema is exported to `docs/openapi/schema.json` via `make export-openapi`.
