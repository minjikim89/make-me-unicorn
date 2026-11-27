"""Vibecheck rules, grouped by the surface they inspect.

`CHECKS` is the run order. Every check takes `(root, code_files, config_files)` and returns
one finding or a list of them.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from mmu_cli.vibecheck.engine import Finding
from mmu_cli.vibecheck.rules.auth import (
    check_admin_routes,
    check_llm_routes,
    check_password_reset,
    check_rate_limiting,
)
from mmu_cli.vibecheck.rules.config import (
    check_cors,
    check_debug_mode,
    check_disabled_ssl,
    check_error_monitoring,
    check_sourcemaps,
    check_stack_trace_leak,
)
from mmu_cli.vibecheck.rules.frontend import check_dangerous_html, check_jwt_localstorage
from mmu_cli.vibecheck.rules.gitconfig import check_git_config_exec
from mmu_cli.vibecheck.rules.injection import (
    check_code_injection,
    check_sql_strings,
    check_unsafe_deserialization,
    deserialization_findings,
)
from mmu_cli.vibecheck.rules.secrets import (
    check_client_bundle_secrets,
    check_env_ignored,
    check_jwt_secret_default,
    check_secrets,
)
from mmu_cli.vibecheck.rules.supabase import check_supabase_rls
from mmu_cli.vibecheck.rules.webhooks import check_webhooks

Check = Callable[[Path, list[Path], list[Path] | None], "Finding | list[Finding]"]

CHECKS: list[Check] = [
    check_secrets,
    check_env_ignored,
    check_jwt_secret_default,
    check_client_bundle_secrets,
    check_webhooks,
    check_password_reset,
    check_sql_strings,
    check_code_injection,
    deserialization_findings,
    check_supabase_rls,
    check_git_config_exec,
    check_rate_limiting,
    check_llm_routes,
    check_admin_routes,
    check_cors,
    check_debug_mode,
    check_error_monitoring,
    check_stack_trace_leak,
    check_dangerous_html,
    check_sourcemaps,
    check_disabled_ssl,
    check_jwt_localstorage,
]

__all__ = [
    "CHECKS",
    "check_admin_routes",
    "check_client_bundle_secrets",
    "check_code_injection",
    "check_cors",
    "check_dangerous_html",
    "check_debug_mode",
    "check_disabled_ssl",
    "check_env_ignored",
    "check_error_monitoring",
    "check_git_config_exec",
    "check_jwt_localstorage",
    "check_jwt_secret_default",
    "check_llm_routes",
    "check_password_reset",
    "check_rate_limiting",
    "check_secrets",
    "check_sourcemaps",
    "check_sql_strings",
    "check_stack_trace_leak",
    "check_supabase_rls",
    "check_unsafe_deserialization",
    "check_webhooks",
    "deserialization_findings",
]
