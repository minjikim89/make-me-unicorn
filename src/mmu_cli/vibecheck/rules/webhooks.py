"""Webhook handler rules: signature verification and idempotency, judged per handler.

A handler is a file that receives provider events (a route that branches on an event
type). Evidence of a safeguard is looked for in that file and in the first-party helpers
it imports, with comments stripped: a verified sibling handler or a TODO never counts.
"""

from __future__ import annotations

import re
from pathlib import Path

from mmu_cli.vibecheck.analysis import (
    JS_SUFFIXES,
    code,
    framework_of,
    is_test_file,
    related_code,
    route_paths,
)
from mmu_cli.vibecheck.engine import Finding, Location, Rule, _rel, loc_at, register

register(Rule(
    id="webhook-signature",
    title="Webhook without signature verification",
    severity="P0",
    summary="A webhook endpoint that does not verify the provider signature accepts forged events, e.g. a fake `checkout.session.completed` that grants paid access.",
    fix=(
        "Verify the provider signature on the raw request body before parsing or trusting the event; return 400 on failure.\n"
        "Use the provider SDK's verifier (Stripe constructEvent / construct_event, Svix Webhook.verify, GitHub "
        "x-hub-signature-256 HMAC compared with a constant-time function) and the signing secret from an env var."
    ),
    fix_variants=(
        ("nextjs", (
            "Verify the signature on the raw body before trusting the event, and return 400 when it fails:\n"
            "event = stripe.webhooks.constructEvent(await req.text(), req.headers.get(\"stripe-signature\")!, process.env.STRIPE_WEBHOOK_SECRET!)\n"
            "Do not call req.json() before this: the check needs the exact bytes the provider signed."
        )),
        ("express", (
            "Mount express.raw({type: \"application/json\"}) on this route (before express.json()), then verify and return 400 on failure:\n"
            "event = stripe.webhooks.constructEvent(req.body, req.headers[\"stripe-signature\"], process.env.STRIPE_WEBHOOK_SECRET)"
        )),
        ("hono", (
            "Verify the signature on the raw body before trusting the event, and return 400 when it fails:\n"
            "event = await stripe.webhooks.constructEventAsync(await c.req.text(), c.req.header(\"stripe-signature\")!, c.env.STRIPE_WEBHOOK_SECRET)"
        )),
        ("fastapi", (
            "Verify the signature on the raw body before trusting the event, and raise HTTPException(400) when it fails:\n"
            "event = stripe.Webhook.construct_event(await request.body(), request.headers[\"stripe-signature\"], settings.stripe_webhook_secret)"
        )),
        ("flask", (
            "Verify the signature on the raw body before trusting the event, and abort(400) when it fails:\n"
            "event = stripe.Webhook.construct_event(request.get_data(), request.headers[\"Stripe-Signature\"], os.environ[\"STRIPE_WEBHOOK_SECRET\"])"
        )),
        ("django", (
            "Verify the signature on the raw body before trusting the event, and return HttpResponse(status=400) when it fails:\n"
            "event = stripe.Webhook.construct_event(request.body, request.META[\"HTTP_STRIPE_SIGNATURE\"], settings.STRIPE_WEBHOOK_SECRET)\n"
            "Keep @csrf_exempt on the view; the signature replaces CSRF protection here."
        )),
    ),
    ref="https://docs.stripe.com/webhooks#verify-official-libraries",
    tags=("webhooks", "payments"),
    confidence="medium",
))

register(Rule(
    id="webhook-idempotency",
    title="Webhook without idempotency",
    severity="P1",
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

# Provider event names: a handler that compares against one of these is receiving provider events.
_EVENT_NAME = re.compile(
    r"""["'`](?:checkout\.session\.\w+|invoice\.(?:paid|payment_\w+|created|finalized|upcoming)|"""
    r"""customer\.subscription\.\w+|payment_intent\.\w+|charge\.(?:succeeded|refunded|failed)|"""
    r"""subscription_(?:created|updated|cancelled|payment_success)|order_created|"""
    r"""user\.(?:created|updated|deleted)|organization\.created|pull_request|"""
    r"""subscription\.(?:created|updated|canceled|active)|transaction\.completed)["'`]"""
)
# An event object's type being read: event.type, req.body.type, payload["type"], event.get("type").
_EVENT_TYPE_READ = re.compile(
    r"""\b(?:event|evt|payload|body|data|webhook\w*|msg|message|notification|json)\w*(?:\.\w+)*"""
    r"""(?:\.(?:type|event|event_type|eventType|event_name|action)\b|\[\s*["'](?:type|event|event_type|event_name)["']\s*\]|"""
    r"""\.get\(\s*["'](?:type|event|event_type)["'])"""
)
_VERIFY_MARKERS = re.compile(
    r"construct_?event|verify_?(?:webhook|signature|header|request|svix|event)|webhooks?\.verify|\.verify(?:Async)?\(|"
    r"x[-_]hub[-_]signature|svix|createhmac|hmac\.(?:new|compare_digest|digest)|\bhmac\b|timingsafeequal|compare_digest|"
    r"crypto\.subtle\.(?:verify|sign)|validate_?(?:request|signature|event|webhook)|webhooks?\.unwrap|unmarshal|"
    r"webhook_?secret|signing_?secret|endpoint_?secret|webhook_?signing|x-webhook-secret|x-signature|signature_?header|"
    r"is_?valid_?signature|check_?signature|verif\w*signature|signature\w*verif|@octokit/webhooks|createnodemiddleware|"
    r"standardwebhooks|webhook_?key|x-api-key|authorization",
    re.IGNORECASE,
)
_IDEMPOTENCY_MARKERS = re.compile(
    r"idempot|event[._]?id\b|event\[[\"']id[\"']\]|evt\.id\b|processed|dedup|already|on\s+conflict|on_?conflict|upsert|"
    r"\bexists\b|findunique|find_?first|get_or_create|setnx|duplicate|unique",
    re.IGNORECASE,
)
# Effects that are wrong when applied twice. A plain "set status = paid" update is naturally idempotent.
_NON_IDEMPOTENT = re.compile(
    r"\.insert\(|\binsert\s+into\b|\.create\(|\.add\(|increment|decrement|\+=|-=|send_?(?:e?mail|message|notification)|"
    r"\.emails?\.send|enqueue|\.publish\(|credits?",
    re.IGNORECASE,
)
_HANDLER = re.compile(
    r"export\s+(?:default\s+)?(?:async\s+)?function\s+(?:POST|handler)\b|export\s+const\s+POST\b|"
    r"\.post\(|@\w+(?:\.\w+)*\.(?:post|route)\(|(?:def|func|function)\s+\w*(?:webhook|hook)\w*",
    re.IGNORECASE,
)
_WEBHOOK_WORD = re.compile(r"web_?hook", re.IGNORECASE)


def _handler_anchor(path: Path, root: Path, text: str) -> Location:
    """The line a webhook finding points at: the route for the webhook path, else the POST handler, else line 1."""
    for pos, route in route_paths(path, root):
        if _WEBHOOK_WORD.search(route) or "hook" in route.lower():
            return loc_at(path, root, text, pos)
    m = _HANDLER.search(text)
    return loc_at(path, root, text, m.start() if m else 0)


def webhook_handlers(root: Path, code_files: list[Path]) -> list[Path]:
    """Files that receive provider webhooks.

    A file qualifies when it declares an HTTP route and reads an event type or compares
    against a provider event name, and either its path, one of its routes or its content
    says "webhook" or a provider event name is present. UI components, clients that
    *send* webhooks and CRUD endpoints for webhook settings do not qualify.
    """
    out: list[Path] = []
    for path in code_files:
        suffix = path.suffix.lower()
        if suffix not in JS_SUFFIXES and suffix != ".py":
            continue
        if is_test_file(path, root):
            continue
        text = code(path)
        has_event_name = _EVENT_NAME.search(text) is not None
        named = _WEBHOOK_WORD.search(_rel(path, root)) is not None
        if not has_event_name and not named and not _WEBHOOK_WORD.search(text):
            continue
        routes = route_paths(path, root)
        if not routes:
            continue
        named = named or any(_WEBHOOK_WORD.search(route) for _, route in routes)
        if not has_event_name and not (named and _EVENT_TYPE_READ.search(text)):
            continue
        out.append(path)
    return out


def check_webhooks(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> list[Finding]:
    handlers = webhook_handlers(root, code_files)
    if not handlers:
        return [
            Finding("webhook-signature", "P0", "skip", "no webhook handlers detected"),
            Finding("webhook-idempotency", "P1", "skip", "no webhook handlers detected"),
        ]
    unsigned: list[Location] = []
    repeatable: list[Location] = []
    for path in handlers:
        text = code(path)
        evidence = related_code(path, root, depth=2)
        if not _VERIFY_MARKERS.search(evidence):
            unsigned.append(_handler_anchor(path, root, text))
        if _NON_IDEMPOTENT.search(text) and not _IDEMPOTENCY_MARKERS.search(evidence):
            repeatable.append(_handler_anchor(path, root, text))
    findings: list[Finding] = []
    n = len(handlers)
    if unsigned:
        findings.append(Finding(
            "webhook-signature",
            "P0",
            "fail",
            f"{len(unsigned)} of {n} webhook handler(s) trust the event without verifying its signature",
            locations=unsigned,
            framework=framework_of(root / unsigned[0].path, root),
        ))
    else:
        findings.append(Finding("webhook-signature", "P0", "ok", f"signature verification found in all {n} webhook handler(s)"))
    if repeatable:
        findings.append(Finding(
            "webhook-idempotency",
            "P1",
            "warn",
            f"{len(repeatable)} of {n} webhook handler(s) apply non-repeatable effects without recording processed event ids",
            locations=repeatable,
        ))
    else:
        findings.append(Finding("webhook-idempotency", "P1", "ok", f"no repeat-unsafe effects found in {n} webhook handler(s)"))
    return findings
