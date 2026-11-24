"""Vibecheck rules, grouped by the surface they inspect."""

from __future__ import annotations

from mmu_cli.vibecheck.rules.auth import check_password_reset, check_rate_limiting
from mmu_cli.vibecheck.rules.config import (
    check_cors,
    check_debug_mode,
    check_disabled_ssl,
    check_error_monitoring,
    check_sourcemaps,
)
from mmu_cli.vibecheck.rules.frontend import check_jwt_localstorage
from mmu_cli.vibecheck.rules.gitconfig import check_git_config_exec
from mmu_cli.vibecheck.rules.injection import check_sql_strings, check_unsafe_deserialization
from mmu_cli.vibecheck.rules.secrets import check_client_bundle_secrets, check_secrets
from mmu_cli.vibecheck.rules.supabase import check_supabase_rls
from mmu_cli.vibecheck.rules.webhooks import check_webhooks

__all__ = [
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
]
