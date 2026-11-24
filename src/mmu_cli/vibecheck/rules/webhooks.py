"""Webhook handler rules: signature verification and idempotency."""

from __future__ import annotations

import re
from pathlib import Path

from mmu_cli.vibecheck.engine import Finding, Rule, first_match_loc, register

register(Rule(
    id="webhook-signature",
    title="Webhook without signature verification",
    severity="P0",
    summary="A webhook endpoint that does not verify the provider signature accepts forged events, e.g. a fake `checkout.session.completed` that grants paid access.",
    fix=(
        "Verify the provider signature on the raw request body before parsing or trusting the event; return 400 on failure.\n"
        "Next.js route: event = stripe.webhooks.constructEvent(await req.text(), req.headers.get(\"stripe-signature\"), process.env.STRIPE_WEBHOOK_SECRET)\n"
        "Express: mount express.raw({type: \"application/json\"}) on the route, then stripe.webhooks.constructEvent(req.body, req.headers[\"stripe-signature\"], secret)\n"
        "FastAPI: event = stripe.Webhook.construct_event(await request.body(), request.headers[\"stripe-signature\"], secret)"
    ),
    ref="https://docs.stripe.com/webhooks#verify-official-libraries",
    tags=("webhooks", "payments"),
    confidence="low",
))

register(Rule(
    id="webhook-idempotency",
    title="Webhook without idempotency",
    severity="P0",
    summary="Providers retry deliveries, so a handler that does not remember processed event ids applies the same payment or fulfilment twice.",
    fix=(
        "Record each processed event id and skip repeats before applying side effects, e.g. "
        "INSERT INTO processed_events (event_id) VALUES ($1) ON CONFLICT DO NOTHING and return 200 early when no row was inserted.\n"
        "Do the insert and the side effect in one transaction so a crash cannot mark an event processed without applying it."
    ),
    ref="https://docs.stripe.com/webhooks#handle-duplicate-events",
    tags=("webhooks", "payments"),
    confidence="low",
))

# The handler line a webhook finding is anchored to (falls back to line 1 of the file).
_HANDLER = re.compile(
    r"export\s+(?:default\s+)?(?:async\s+)?function\s+(?:POST|handler)\b|export\s+const\s+POST\b|"
    r"\.post\(|@\w+(?:\.\w+)*\.(?:post|route)\(|(?:def|func|function)\s+\w*webhook\w*",
    re.IGNORECASE,
)


def check_webhooks(root: Path, code_files: list[Path]) -> list[Finding]:
    from mmu_cli.cli import check_webhook_safety, detect_webhook_files

    webhook_files = detect_webhook_files(root, code_files)
    if not webhook_files:
        return [
            Finding("webhook-signature", "P0", "skip", "no webhook handlers detected"),
            Finding("webhook-idempotency", "P0", "skip", "no webhook handlers detected"),
        ]
    errors: list[str] = []
    has_sig, has_idem = check_webhook_safety(webhook_files, errors)
    findings = []
    if has_sig:
        findings.append(Finding("webhook-signature", "P0", "ok", "webhook signature verification markers found"))
    else:
        findings.append(
            Finding(
                "webhook-signature",
                "P0",
                "fail",
                "webhook handlers found but no signature verification markers",
                locations=[first_match_loc(p, root, _HANDLER) for p in webhook_files],
            )
        )
    if has_idem:
        findings.append(Finding("webhook-idempotency", "P0", "ok", "webhook idempotency markers found"))
    else:
        findings.append(
            Finding(
                "webhook-idempotency",
                "P0",
                "fail",
                "webhook handlers found but no idempotency markers",
                locations=[first_match_loc(p, root, _HANDLER) for p in webhook_files],
            )
        )
    return findings
