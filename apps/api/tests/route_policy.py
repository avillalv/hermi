# ruff: noqa: E501  (long comments)
"""Every route's tenancy class (10 section 1.3 item 6). A new route fails tests/tenancy until it is added here.

Classes:
- tenant: acts on a trip or its children. Another user gets 404, a viewer cannot write, no token gets 401.
- user_scoped: acts on the caller's own account. Another user only ever sees their own data.
- public: needs no token (health, waitlist, docs, local dev routes).
- token_feed: authorized by a secret in the URL (calendar feeds, share links). Tested by scenario 18.
- webhook: authorized by a shared secret or signature. Tested by the contract suite.
- admin: tested by the admin suite.

Key: "METHOD /path" exactly as FastAPI registers it. Later prompts add one line per route.
"""

CLASSES = ("tenant", "user_scoped", "public", "token_feed", "webhook", "admin")

POLICY: dict[str, str] = {
    "GET /health/live": "public",
    "GET /health/ready": "public",
    "POST /v1/waitlist": "public",
    "POST /v1/me/bootstrap": "user_scoped",
    "GET /v1/me": "user_scoped",
    "GET /v1/me/entitlements": "user_scoped",
    "GET /v1/geo/destinations": "user_scoped",
    "GET /v1/trips": "user_scoped",
    "POST /v1/trips": "user_scoped",
    "GET /v1/trips/{trip_id}": "tenant",
    "PATCH /v1/trips/{trip_id}": "tenant",
    "DELETE /v1/trips/{trip_id}": "tenant",
    "POST /v1/trips/{trip_id}/restore": "tenant",
    "POST /v1/trips/{trip_id}/duplicate": "tenant",
    "GET /v1/trips/{trip_id}/destinations": "tenant",
    "POST /v1/trips/{trip_id}/destinations": "tenant",
    "PUT /v1/trips/{trip_id}/destinations/order": "tenant",
    "PATCH /v1/trips/{trip_id}/destinations/{destination_id}": "tenant",
    "DELETE /v1/trips/{trip_id}/destinations/{destination_id}": "tenant",
    "GET /v1/people": "user_scoped",
    "POST /v1/people": "user_scoped",
    "PUT /v1/people/{person_id}": "user_scoped",
    "DELETE /v1/people/{person_id}": "user_scoped",
    "PUT /v1/trips/{trip_id}/travelers": "tenant",
    "PUT /v1/trips/{trip_id}/members/me/traveler": "tenant",
    "DELETE /v1/trips/{trip_id}/members/me/traveler": "tenant",
    # Mounted only when AUTH_MODE=dev in local and ci (main.create_app).
    "GET /v1/dev/personas": "public",
    "POST /v1/dev/session": "public",
    # FastAPI's own documentation routes.
    "GET /openapi.json": "public",
    "GET /docs": "public",
    "GET /docs/oauth2-redirect": "public",
    "GET /redoc": "public",
}

# Tenant write routes a viewer may call (04 role table: a viewer can read and heart). "METHOD /path" keys.
VIEWER_WRITE_OK: set[str] = {"PUT /v1/trips/{trip_id}/members/me/traveler", "DELETE /v1/trips/{trip_id}/members/me/traveler"}  # a viewer says which traveler they are
