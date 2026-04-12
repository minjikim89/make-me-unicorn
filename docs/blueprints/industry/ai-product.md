# AI Product Blueprint

> Additional checklist for SaaS products powered by LLMs, ML models, or AI APIs.
> Use alongside the core 15 blueprints — this covers AI-specific blind spots.

## Model & API Integration

- [ ] [P0] API key stored in env vars, never in client-side code.
- [ ] [P0] Rate limiting on AI endpoints (prevent cost explosion).
- [ ] [P0] Timeout and fallback for model API calls (30s max recommended).
- [ ] [P1] Streaming response support for long-running generations.
- [ ] [P1] Token usage tracking per request (for cost attribution).
- [ ] [P1] Model version pinning (avoid silent behavior changes on upgrades).
- [ ] [P2] Multi-provider fallback (e.g., Claude → GPT → local model).
- [ ] [P2] Prompt versioning system (track what prompt produced what output).

## Cost Control

- [ ] [P0] Per-user usage limits (daily/monthly token caps).
- [ ] [P0] Cost alerting when spend exceeds threshold.
- [ ] [P1] Usage dashboard visible to end users ("X credits remaining").
- [ ] [P1] Tiered pricing aligned with AI usage (free tier = limited calls).
- [ ] [P1] Caching layer for repeated/similar queries (reduce redundant API calls).
- [ ] [P2] Batch processing option for non-urgent requests (cheaper).

## Prompt Engineering & Quality

- [ ] [P0] System prompts reviewed for injection vulnerabilities.
- [ ] [P0] User input sanitized before inclusion in prompts.
- [ ] [P1] Output validation — check AI response structure before displaying.
- [ ] [P1] Hallucination guardrails (citations, confidence scores, or disclaimers).
- [ ] [P1] A/B testing framework for prompt variants.
- [ ] [P2] Human-in-the-loop option for high-stakes outputs.
- [ ] [P2] Evaluation dataset for measuring output quality over time.

## User Experience

- [ ] [P0] Loading indicator during AI generation (skeleton or streaming).
- [ ] [P0] Clear error state when AI service is unavailable.
- [ ] [P1] "Regenerate" button for unsatisfactory outputs.
- [ ] [P1] Edit/refine workflow — let users modify AI output before accepting.
- [ ] [P1] Feedback mechanism (thumbs up/down on AI responses).
- [ ] [P2] History of past AI interactions accessible to user.
- [ ] [P2] Export/copy AI-generated content in multiple formats.

## Data & Privacy

- [ ] [P0] Disclose AI usage in privacy policy ("your data may be sent to X API").
- [ ] [P0] No PII sent to third-party AI APIs without user consent.
- [ ] [P1] Data retention policy for AI inputs/outputs.
- [ ] [P1] Option to opt out of data being used for model training.
- [ ] [P1] Audit log of AI API calls (for compliance and debugging).
- [ ] [P2] On-premise / self-hosted model option for enterprise customers.

## Reliability & Monitoring

- [ ] [P0] Monitor AI API latency and error rates separately.
- [ ] [P0] Graceful degradation when AI service is down (app still usable).
- [ ] [P1] Alert on sudden cost spikes or unusual usage patterns.
- [ ] [P1] Log prompt + response pairs for debugging (redact PII).
- [ ] [P2] Shadow testing — run new model versions alongside production.
- [ ] [P2] Canary deployment for prompt changes.

## Ethical & Legal

- [ ] [P1] AI-generated content labeled as such where required.
- [ ] [P1] Bias review for model outputs affecting user decisions.
- [ ] [P2] Compliance with EU AI Act risk classification (if targeting EU).
- [ ] [P2] Accessibility of AI features (screen reader support for generated content).
