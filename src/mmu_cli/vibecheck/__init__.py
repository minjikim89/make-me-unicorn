"""`mmu vibecheck` — fast scan for the failure modes AI-generated code ships most.

Heuristic, zero-dependency, read-only. Each check answers one question a solo
builder forgets to ask before launch: leaked secrets, unverified webhooks,
missing password reset, no rate limiting, wildcard CORS, f-string SQL,
debug mode left on, no error monitoring, secrets behind public env prefixes,
Supabase tables without RLS, production source maps, command-executing
`.git/config` keys.

Checks carry a `ref` — the incident report or dataset that motivated them — so a
finding is never "the tool says so" but "here is what happened to people who shipped this".

Severities: P0 findings exit non-zero (block launch), P1 findings warn.
Checks that find no relevant surface (e.g. no webhook handlers) report SKIP.
"""


from __future__ import annotations

from mmu_cli.vibecheck.engine import (
    _READ_CACHE,
    Finding,
    _is_test_path,
    _read,
    _rel,
    downgrade_test_only_findings,
    run_vibecheck,
)
from mmu_cli.vibecheck.output import format_findings
from mmu_cli.vibecheck.rules import (
    check_client_bundle_secrets,
    check_cors,
    check_debug_mode,
    check_disabled_ssl,
    check_error_monitoring,
    check_git_config_exec,
    check_jwt_localstorage,
    check_password_reset,
    check_rate_limiting,
    check_secrets,
    check_sourcemaps,
    check_sql_strings,
    check_supabase_rls,
    check_unsafe_deserialization,
    check_webhooks,
)

__all__ = [
    "_READ_CACHE",
    "Finding",
    "_is_test_path",
    "_read",
    "_rel",
    "check_client_bundle_secrets",
    "check_cors",
    "check_debug_mode",
    "check_disabled_ssl",
    "check_error_monitoring",
    "check_git_config_exec",
    "check_jwt_localstorage",
    "check_password_reset",
    "check_rate_limiting",
    "check_secrets",
    "check_sourcemaps",
    "check_sql_strings",
    "check_supabase_rls",
    "check_unsafe_deserialization",
    "check_webhooks",
    "downgrade_test_only_findings",
    "format_findings",
    "run_vibecheck",
]
