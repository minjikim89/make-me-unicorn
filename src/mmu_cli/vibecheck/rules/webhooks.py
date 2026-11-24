"""Webhook handler rules: signature verification and idempotency."""

from __future__ import annotations

from pathlib import Path

from mmu_cli.vibecheck.engine import Finding, _rel

def check_webhooks(root: Path, code_files: list[Path]) -> list[Finding]:
    from mmu_cli.cli import check_webhook_safety, detect_webhook_files

    webhook_files = detect_webhook_files(root, code_files)
    if not webhook_files:
        return [Finding("webhook-safety", "P0", "skip", "no webhook handlers detected")]
    errors: list[str] = []
    has_sig, has_idem = check_webhook_safety(webhook_files, errors)
    rels = [_rel(p, root) for p in webhook_files]
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
                hint="Verify provider signatures (e.g. stripe.webhooks.constructEvent) or attackers can forge payment events.",
                files=rels,
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
                hint="Store processed event IDs — providers retry deliveries, and double-processing a payment event is a refund ticket.",
                files=rels,
            )
        )
    return findings
