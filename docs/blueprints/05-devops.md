# DevOps Blueprint

> Deep-dive checklist for infrastructure, deployment, and environment management.
> Gate-level checks → `docs/checklists/from_scratch.md`

## Environment Strategy

- [ ] Define `dev/staging/prod` environments.
- [ ] Create `.env.example` with all required variables documented.
- [ ] Never commit secrets to source control.
- [ ] Use environment-specific configuration files.
- [ ] Implement environment variable validation at startup.

## Hosting and Compute

- [ ] Choose hosting provider (Vercel, Railway, Fly.io, AWS).
- [ ] Configure auto-scaling rules if applicable.
- [ ] Set memory and CPU limits per service.
- [ ] Configure health check endpoints.
- [ ] Set up custom domain with DNS.

## Containerization

- [ ] Create `Dockerfile` with multi-stage builds.
- [ ] Use `.dockerignore` to exclude unnecessary files.
- [ ] Pin base image versions for reproducibility.
- [ ] Run container as non-root user.
- [ ] Configure container resource limits.

## Database Operations

- [ ] Automate database migrations in deployment pipeline.
- [ ] Set up automated database backups (daily minimum).
- [ ] Test backup restoration procedure.
- [ ] Configure connection pooling for production.
- [ ] Implement database monitoring and slow query alerts.

## DNS and SSL

- [ ] Configure DNS records (A, CNAME, MX).
- [ ] Enable HTTPS with auto-renewing SSL certificates.
- [ ] Set up `www` to apex domain redirect (or vice versa).
- [ ] Configure HSTS headers.
- [ ] Add CAA DNS records for certificate authority restriction.

## Secrets Management

- [ ] Use secrets manager (Doppler, Vault, or provider-native).
- [ ] Rotate API keys and secrets on a schedule.
- [ ] Audit access to secrets.
- [ ] Never log secrets in application output.
- [ ] Use different secrets per environment.

## Infrastructure as Code

- [ ] Define infrastructure with IaC (Terraform, Pulumi, or SST).
- [ ] Store IaC state remotely with locking.
- [ ] Review infrastructure changes before applying.
- [ ] Tag resources for cost tracking.

## Rollback Strategy

- [ ] Implement zero-downtime deployments (rolling or blue-green).
- [ ] Define rollback procedure and test it.
- [ ] Keep previous deployment artifacts for quick rollback.
- [ ] Implement database migration rollback scripts.
- [ ] Document rollback decision criteria.

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| Vercel | Frontend Hosting | Free tier | Zero-config Next.js deployment |
| Railway | Backend Hosting | $5/mo+ | Simple container deployment |
| Fly.io | Edge Hosting | Free tier | Global edge deployment |
| Docker | Containerization | Free | Reproducible builds |
| Terraform | IaC | Free | Multi-cloud infrastructure management |
| Doppler | Secrets Management | Free tier | Centralized secrets across environments |
| Cloudflare | DNS/CDN | Free tier | Fast DNS, DDoS protection, CDN |
