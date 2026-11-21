# API contract — DeInklings frontend ↔ Python backend

The frontend (`src/lib/api/*`) is already built against this contract. Implement
a Flask app that satisfies it and the UI needs no further changes. Base URL is
read from `VITE_API_BASE_URL` (see `.env`), default `http://localhost:8000`.

## Conventions

- All request/response bodies are JSON.
- Authenticated endpoints require `Authorization: Bearer <access_token>`.
- Field names are **camelCase** in JSON (the frontend types in
  `src/lib/api/types.ts` are the source of truth); the Postgres columns in
  `backend-contract/schema.sql` are snake_case — convert at the API boundary.
- Errors: any non-2xx response should return `{"message": "..."}` (or
  `"error"`); the frontend reads `data.message ?? data.error`.
- CORS: enable it for the Vite dev origin (and your deployed frontend origin),
  allowing `Authorization` and `Content-Type` headers.

## Auth

### `POST /api/auth/signup`
Request: `{ name, email, password, account_type: "storyteller" | "creative" }`
Response `200`: `{ accessToken, user }` — see `User` shape below.
Create the user with a hashed password, a role, and a JWT (e.g. `PyJWT`) whose
`sub` claim is the user id.

### `POST sd`
Request: `{ email, password }` → Response: `{ accessToken, user }`.

### `GET /api/auth/me` (auth required)
Response: `User`:
```json
{ "id": "...", "email": "...", "displayName": "...", "role": "storyteller", "createdAt": "..." }
```
Used by the frontend as the source of truth for "am I signed in" — invalid/expired
tokens should return `401`, which the frontend treats as signed-out.

## Listings

### `GET /api/listings?q=&format=&genre=&mood=&adaptation_type=`
Public (no auth). Returns `Listing[]`, filtered server-side by any provided
query params (`adaptation_type` matches against the `mediums` array).

### `GET /api/listings/:id`
Public. Returns one `Listing`, or `404` (frontend treats 404 as "not found").

### `GET /api/listings/mine` (auth required)
Returns the signed-in user's own `Listing[]` regardless of format/genre filters.

### `POST /api/listings` (auth required, role must be `storyteller`)
Request body (`CreateListingInput`):
```json
{
  "title": "...", "format": "...", "genre": "...", "mood": "...",
  "body": "...", "logline": "...", "synopsis": "...",
  "tags": ["..."], "mediums": ["..."],
  "openToAdaptation": true, "openToCollaboration": false, "openToLicensing": false
}
```
Response: the created `Listing` (with generated `id`, `ownerId`, `ownerName`
from the user's profile, `createdAt`).

### `PATCH /api/listings/:id` (auth, owner only)
Partial `CreateListingInput`. Returns updated `Listing`.

### `DELETE /api/listings/:id` (auth, owner only)
`204 No Content`.

### `Listing` shape
```json
{
  "id": "...", "ownerId": "...", "ownerName": "...", "ownerNote": "...",
  "title": "...", "format": "...", "genre": "...", "mood": "...",
  "body": "...", "logline": "...", "synopsis": "...",
  "tags": ["..."], "mediums": ["..."],
  "openToAdaptation": true, "openToCollaboration": false, "openToLicensing": false,
  "coverUrl": null, "createdAt": "2026-01-01T00:00:00Z"
}
```
`ownerNote` is a short creator bio — can come from a future `users.bio` column;
return `""` until that exists.

## Adaptation requests

### `POST /api/adaptation-requests` (auth, role must be `creative`)
Request: `{ listing_id, medium, message }`.
Server must look up `owner_id` from the referenced listing (never trust a
client-supplied owner), and reject with `400`/`403` if the listing isn't
`open_to_adaptation`. Returns the created `AdaptationRequest`.

### `GET /api/adaptation-requests/sent` (auth)
Requests created by the signed-in user. Returns `AdaptationRequest[]`.

### `GET /api/adaptation-requests/received` (auth)
Requests where the signed-in user is the listing owner. Returns `AdaptationRequest[]`.

### `PATCH /api/adaptation-requests/:id` (auth, owner only)
Request: `{ status: "accepted" | "declined" }`. Set `responded_at = now()`.
Returns the updated `AdaptationRequest`.

### `AdaptationRequest` shape
```json
{
  "id": "...", "listingId": "...", "listingTitle": "...",
  "requesterId": "...", "requesterName": "...",
  "ownerId": "...", "ownerName": "...",
  "medium": "...", "message": "...",
  "status": "pending", "createdAt": "...", "respondedAt": null
}
```

## Suggested Flask stack

- **Flask** + **Flask-SQLAlchemy** (or raw `psycopg`) against
  `backend-contract/schema.sql`.
- **Flask-JWT-Extended** (or `PyJWT` directly) for the bearer token.
- **Flask-CORS** for the dev/prod frontend origins.
- **Alembic** (via Flask-Migrate) if you want migrations instead of the raw
  SQL file — the SQL file is a starting point, not a requirement.
- Password hashing: `werkzeug.security.generate_password_hash` /
  `check_password_hash` is sufficient to start.
