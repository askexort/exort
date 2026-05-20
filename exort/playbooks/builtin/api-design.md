# REST API Design Guide

## URL Structure
- Use nouns, not verbs: `/users` not `/getUsers`
- Plural for collections: `/users`, `/orders`
- Nest for relationships: `/users/123/orders`
- Use query params for filtering: `/users?role=admin`

## HTTP Methods
- GET — read (idempotent)
- POST — create
- PUT — full update (idempotent)
- PATCH — partial update
- DELETE — remove (idempotent)

## Response Format
```json
{
  "data": { ... },
  "meta": { "page": 1, "total": 100 },
  "error": null
}
```

## Status Codes
- 200 OK — success
- 201 Created — resource created
- 400 Bad Request — client error
- 401 Unauthorized — no auth
- 403 Forbidden — no permission
- 404 Not Found — doesn't exist
- 422 Unprocessable — validation error
- 500 Internal Error — server bug

## Best Practices
- Version your API: `/v1/users`
- Rate limiting with headers
- Pagination for collections
- Consistent error format
- CORS headers for browsers
