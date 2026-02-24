# Backend Blueprint

> Deep-dive checklist for backend API, database, caching, and job processing.
> Gate-level checks → `docs/checklists/from_scratch.md`

## API Design

- [ ] Choose API style (REST, GraphQL, or tRPC).
- [ ] Define consistent URL naming convention (`/api/v1/resource`).
- [ ] Implement standard error response shape (`{ error, code, message }`).
- [ ] Version API endpoints from day one.
- [ ] Add request ID to every response for tracing.
- [ ] Document API endpoints (OpenAPI/Swagger or equivalent).

## Request Handling

- [ ] Validate all incoming payloads with schema validation (Zod, Joi).
- [ ] Sanitize user input to prevent injection attacks.
- [ ] Implement rate limiting per endpoint and per user.
- [ ] Add request size limits to prevent abuse.
- [ ] Handle CORS configuration for allowed origins.
- [ ] Implement pagination for list endpoints (cursor or offset).

## Database

- [ ] Choose database (PostgreSQL, MySQL, or MongoDB).
- [ ] Set up ORM/query builder (Prisma, Drizzle, or TypeORM).
- [ ] Configure connection pooling.
- [ ] Create migration workflow (up/down scripts).
- [ ] Add indexes for frequently queried columns.
- [ ] Implement soft delete for user-facing data.
- [ ] Set up database seed scripts for development.
- [ ] Configure `dev/staging/prod` database separation.

## Authentication and Authorization Middleware

- [ ] Implement JWT or session-based auth middleware.
- [ ] Add role-based access control (RBAC) middleware.
- [ ] Protect all sensitive endpoints with auth checks.
- [ ] Implement API key authentication for service-to-service calls.

## Background Jobs and Queues

- [ ] Choose job queue (BullMQ, Inngest, or Trigger.dev).
- [ ] Implement retry logic with exponential backoff.
- [ ] Add dead letter queue for failed jobs.
- [ ] Log job execution with duration and outcome.
- [ ] Implement idempotency keys for critical operations.

## Caching

- [ ] Implement response caching strategy (Redis or in-memory).
- [ ] Define cache invalidation rules per resource.
- [ ] Add cache headers for static API responses.
- [ ] Cache expensive database queries.

## File Storage

- [ ] Choose storage provider (S3, R2, or GCS).
- [ ] Implement signed URL generation for uploads.
- [ ] Add file type and size validation.
- [ ] Configure CDN for public file delivery.

## Webhooks (Outgoing)

- [ ] Implement webhook event dispatching.
- [ ] Add retry logic for failed webhook deliveries.
- [ ] Sign outgoing webhooks with HMAC.
- [ ] Log all webhook delivery attempts.

## Logging and Error Handling

- [ ] Implement structured logging (JSON format).
- [ ] Add correlation IDs across request lifecycle.
- [ ] Configure log levels (`debug`, `info`, `warn`, `error`).
- [ ] Capture unhandled exceptions with stack traces.
- [ ] Avoid logging sensitive data (passwords, tokens, PII).

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| Node.js + Express/Fastify | Runtime + Framework | Free | Mature ecosystem, async I/O |
| Prisma | ORM | Free | Type-safe queries, auto migrations |
| PostgreSQL | Database | Free | Reliable, full-featured RDBMS |
| Redis | Cache/Queue | Free | In-memory speed, pub/sub support |
| BullMQ | Job Queue | Free | Redis-backed, retry and scheduling |
| Zod | Validation | Free | Shared schemas with frontend |
| AWS S3 / Cloudflare R2 | File Storage | Pay-as-you-go | Scalable object storage |
| Pino | Logging | Free | Fast structured JSON logging |
