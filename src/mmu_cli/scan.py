"""Auto-detect tech stack and pre-check blueprint items."""

from __future__ import annotations

import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _has_file(root: Path, *names: str) -> bool:
    return any((root / n).is_file() for n in names)


def _has_dir(root: Path, *names: str) -> bool:
    return any((root / n).is_dir() for n in names)


def _pkg_deps(root: Path) -> set[str]:
    """Return all dependency names from package.json."""
    text = _read(root / "package.json")
    if not text:
        return set()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return set()
    deps: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        section = data.get(key, {})
        if isinstance(section, dict):
            deps.update(section.keys())
    return deps


def _py_deps(root: Path) -> set[str]:
    """Return dependency names from requirements.txt or pyproject.toml."""
    deps: set[str] = set()
    # requirements.txt
    for name in ("requirements.txt", "requirements/base.txt", "requirements/prod.txt"):
        text = _read(root / name)
        if text:
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name before version specifier
                    pkg = re.split(r"[>=<!\[\s]", line)[0].lower().strip()
                    if pkg:
                        deps.add(pkg)
    # pyproject.toml (basic parsing)
    text = _read(root / "pyproject.toml")
    if text:
        in_deps = False
        for line in text.splitlines():
            if re.match(r"^\s*dependencies\s*=\s*\[", line):
                in_deps = True
                continue
            if in_deps:
                if "]" in line:
                    in_deps = False
                m = re.match(r'^\s*"([^">=<!\[]+)', line)
                if m:
                    deps.add(m.group(1).lower().strip())
    return deps


def _file_contains(root: Path, rel: str, *patterns: str) -> bool:
    text = _read(root / rel)
    if not text:
        return False
    text_lower = text.lower()
    return any(p.lower() in text_lower for p in patterns)


def _any_file_contains(root: Path, globs: list[str], *patterns: str) -> bool:
    for g in globs:
        for path in root.glob(g):
            if path.is_file():
                text = _read(path)
                if text and any(p.lower() in text.lower() for p in patterns):
                    return True
    return False


# ---------------------------------------------------------------------------
# Detection rules: (signal_name, detector_fn)
# Each detector returns True if the signal is present.
# ---------------------------------------------------------------------------


def _build_detectors(root: Path) -> dict[str, bool]:
    """Run all detectors and return {signal: bool}."""
    npm = _pkg_deps(root)
    py = _py_deps(root)
    all_deps = npm | py

    signals: dict[str, bool] = {}

    # -- Frameworks --
    signals["react"] = "react" in npm
    signals["nextjs"] = "next" in npm
    signals["vue"] = "vue" in npm
    signals["svelte"] = "svelte" in npm or "@sveltejs/kit" in npm
    signals["angular"] = "@angular/core" in npm
    signals["fastapi"] = "fastapi" in py
    signals["django"] = "django" in py
    signals["flask"] = "flask" in py
    signals["express"] = "express" in npm

    # -- Languages --
    signals["typescript"] = "typescript" in npm or _has_file(root, "tsconfig.json")
    signals["python"] = bool(py) or _has_file(root, "pyproject.toml", "setup.py", "requirements.txt")

    # -- CSS/UI --
    signals["tailwind"] = "tailwindcss" in npm or _has_file(root, "tailwind.config.js", "tailwind.config.ts")
    signals["shadcn"] = _has_dir(root, "components/ui") or _has_dir(root, "src/components/ui")
    signals["radix"] = any(d.startswith("@radix-ui") for d in npm)

    # -- State / Data --
    signals["tanstack_query"] = "@tanstack/react-query" in npm
    signals["redux"] = "redux" in npm or "@reduxjs/toolkit" in npm
    signals["zustand"] = "zustand" in npm

    # -- Forms --
    signals["react_hook_form"] = "react-hook-form" in npm
    signals["zod"] = "zod" in npm or "zod" in py
    signals["pydantic"] = "pydantic" in py

    # -- Router --
    signals["react_router"] = "react-router-dom" in npm or "react-router" in npm

    # -- Auth --
    signals["supabase_auth"] = "@supabase/supabase-js" in npm or "supabase" in py or "gotrue" in py
    signals["firebase_auth"] = "firebase" in npm or "firebase-admin" in py
    signals["auth0"] = "@auth0/auth0-react" in npm or "auth0" in py
    signals["clerk"] = "@clerk/nextjs" in npm or "@clerk/clerk-react" in npm
    signals["nextauth"] = "next-auth" in npm

    # -- Database --
    signals["postgresql"] = (
        "pg" in npm or "postgres" in npm or "psycopg2" in py or "psycopg2-binary" in py
        or "asyncpg" in py or "sqlalchemy" in py
        or _file_contains(root, ".env.example", "POSTGRES", "postgresql")
        or _file_contains(root, ".env", "POSTGRES", "postgresql")
    )
    signals["mongodb"] = "mongoose" in npm or "mongodb" in npm or "pymongo" in py
    signals["mysql"] = "mysql2" in npm or "mysqlclient" in py
    signals["sqlite"] = "better-sqlite3" in npm or "sqlite3" in py
    signals["supabase_db"] = signals["supabase_auth"]  # Usually implies Supabase PG
    signals["prisma"] = "prisma" in npm or "@prisma/client" in npm
    signals["drizzle"] = "drizzle-orm" in npm
    signals["sqlalchemy"] = "sqlalchemy" in py
    signals["typeorm"] = "typeorm" in npm

    # -- Payment --
    signals["stripe"] = "stripe" in npm or "stripe" in py
    signals["lemon_squeezy"] = (
        "@lemonsqueezy/lemonsqueezy.js" in npm
        or _any_file_contains(root, ["**/*.py", "**/*.ts", "**/*.js"], "lemonsqueezy", "lemon_squeezy")
    )
    signals["paddle"] = "paddle" in all_deps

    # -- Email --
    signals["resend"] = "resend" in npm or "resend" in py
    signals["sendgrid"] = "@sendgrid/mail" in npm or "sendgrid" in py
    signals["postmark"] = "postmark" in npm or "postmarker" in py
    signals["nodemailer"] = "nodemailer" in npm

    # -- Monitoring --
    signals["sentry"] = "@sentry/react" in npm or "@sentry/node" in npm or "sentry-sdk" in py
    signals["posthog"] = "posthog-js" in npm or "posthog" in py

    # -- Testing --
    signals["vitest"] = "vitest" in npm
    signals["jest"] = "jest" in npm
    signals["playwright"] = "@playwright/test" in npm or "playwright" in py
    signals["cypress"] = "cypress" in npm
    signals["pytest"] = "pytest" in py

    # -- Animation --
    signals["framer_motion"] = "framer-motion" in npm

    # -- CI/CD --
    signals["github_actions"] = _has_dir(root, ".github/workflows")
    signals["docker"] = _has_file(root, "Dockerfile", "docker-compose.yml", "docker-compose.yaml")

    # -- Hosting --
    signals["vercel"] = _has_file(root, "vercel.json") or _has_dir(root, ".vercel")
    signals["railway"] = _file_contains(root, "railway.toml", "railway") or _file_contains(root, "railway.json", "railway")
    signals["netlify"] = _has_file(root, "netlify.toml")

    # -- SEO / Marketing --
    signals["robots_txt"] = _has_file(root, "public/robots.txt", "static/robots.txt", "robots.txt")
    signals["sitemap"] = _has_file(root, "public/sitemap.xml", "static/sitemap.xml", "sitemap.xml")
    signals["og_meta"] = _any_file_contains(
        root, ["src/**/*.tsx", "src/**/*.jsx", "app/**/*.tsx", "**/*.html"],
        "og:title", "og:image", "openGraph", "open_graph",
    )
    signals["ga4"] = _any_file_contains(
        root, ["src/**/*.tsx", "src/**/*.jsx", "**/*.html", "**/*.ts", "**/*.js"],
        "G-", "gtag", "google-analytics", "GoogleAnalytics",
    )

    # -- Security --
    signals["cors"] = _any_file_contains(
        root, ["**/*.py", "**/*.ts", "**/*.js"],
        "cors", "CORSMiddleware", "Access-Control-Allow",
    )
    signals["rate_limiting"] = _any_file_contains(
        root, ["**/*.py", "**/*.ts", "**/*.js"],
        "rate_limit", "rateLimit", "throttle", "Limiter",
    )
    signals["jwt"] = _any_file_contains(
        root, ["**/*.py", "**/*.ts", "**/*.js"],
        "jwt", "jsonwebtoken", "JWT", "Bearer",
    )
    signals["https_ssl"] = _any_file_contains(
        root, ["**/*.py", "**/*.ts", "**/*.js", "**/*.toml", "**/*.yaml"],
        "https://", "ssl", "tls", "certificate",
    )

    # -- Webhook --
    signals["webhook_handler"] = _any_file_contains(
        root, ["**/*.py", "**/*.ts", "**/*.js"],
        "webhook",
    )
    signals["webhook_signature"] = _any_file_contains(
        root, ["**/*.py", "**/*.ts", "**/*.js"],
        "verify_signature", "constructEvent", "x-signature", "webhook_secret", "hmac",
    )

    # -- Legal --
    signals["privacy_policy"] = _any_file_contains(
        root, ["src/**/*.tsx", "src/**/*.jsx", "**/*.html", "**/*.md"],
        "privacy policy", "privacy-policy", "PrivacyPolicy",
    )
    signals["terms_of_service"] = _any_file_contains(
        root, ["src/**/*.tsx", "src/**/*.jsx", "**/*.html", "**/*.md"],
        "terms of service", "terms-of-service", "TermsOfService",
    )

    # -- Logging --
    signals["structured_logging"] = _any_file_contains(
        root, ["**/*.py", "**/*.ts", "**/*.js"],
        "structlog", "winston", "pino", "logging.getLogger", "logger",
    )

    # -- Health check --
    signals["health_check"] = _any_file_contains(
        root, ["**/*.py", "**/*.ts", "**/*.js"],
        "/health", "healthcheck", "health_check",
    )

    return signals


# ---------------------------------------------------------------------------
# Signal → Blueprint item mapping
# Each rule: (signal, blueprint_filename, item_substring_to_match)
# If signal is True and an unchecked item matching the substring exists,
# it gets auto-checked.
# ---------------------------------------------------------------------------

SCAN_RULES: list[tuple[str, str, str]] = [
    # -- Frontend --
    ("react", "01-frontend.md", "Choose framework"),
    ("react", "01-frontend.md", "framework"),
    ("typescript", "01-frontend.md", "TypeScript"),
    ("tailwind", "01-frontend.md", "CSS strategy"),
    ("tailwind", "01-frontend.md", "CSS"),
    ("shadcn", "01-frontend.md", "component library"),
    ("radix", "01-frontend.md", "component library"),
    ("react_router", "01-frontend.md", "routing"),
    ("react_router", "01-frontend.md", "Routing"),
    ("react_router", "01-frontend.md", "route guards"),
    ("tanstack_query", "01-frontend.md", "server state"),
    ("tanstack_query", "01-frontend.md", "caching"),
    ("react_hook_form", "01-frontend.md", "form library"),
    ("zod", "01-frontend.md", "validation"),
    ("zod", "01-frontend.md", "schema validation"),
    ("framer_motion", "01-frontend.md", "animation"),

    # -- Backend --
    ("fastapi", "02-backend.md", "API style"),
    ("fastapi", "02-backend.md", "framework"),
    ("fastapi", "02-backend.md", "Choose"),
    ("django", "02-backend.md", "API style"),
    ("django", "02-backend.md", "framework"),
    ("express", "02-backend.md", "API style"),
    ("pydantic", "02-backend.md", "validation"),
    ("pydantic", "02-backend.md", "Validation"),
    ("sqlalchemy", "02-backend.md", "ORM"),
    ("prisma", "02-backend.md", "ORM"),
    ("drizzle", "02-backend.md", "ORM"),
    ("typeorm", "02-backend.md", "ORM"),
    ("postgresql", "02-backend.md", "database"),
    ("postgresql", "02-backend.md", "Database"),
    ("postgresql", "02-backend.md", "Choose database"),
    ("mongodb", "02-backend.md", "database"),
    ("cors", "02-backend.md", "CORS"),
    ("rate_limiting", "02-backend.md", "rate limit"),
    ("structured_logging", "02-backend.md", "logging"),
    ("structured_logging", "02-backend.md", "Logging"),
    ("health_check", "02-backend.md", "health"),

    # -- Auth --
    ("supabase_auth", "03-auth.md", "auth provider"),
    ("supabase_auth", "03-auth.md", "Choose"),
    ("firebase_auth", "03-auth.md", "auth provider"),
    ("auth0", "03-auth.md", "auth provider"),
    ("clerk", "03-auth.md", "auth provider"),
    ("jwt", "03-auth.md", "JWT"),
    ("jwt", "03-auth.md", "token"),
    ("jwt", "03-auth.md", "session"),

    # -- Billing --
    ("stripe", "04-billing.md", "payment provider"),
    ("stripe", "04-billing.md", "Choose"),
    ("stripe", "04-billing.md", "Provider"),
    ("lemon_squeezy", "04-billing.md", "payment provider"),
    ("lemon_squeezy", "04-billing.md", "Choose"),
    ("lemon_squeezy", "04-billing.md", "Provider"),
    ("webhook_signature", "04-billing.md", "signature"),
    ("webhook_signature", "04-billing.md", "Signature"),
    ("webhook_handler", "04-billing.md", "webhook"),

    # -- DevOps --
    ("docker", "05-devops.md", "Docker"),
    ("docker", "05-devops.md", "container"),
    ("vercel", "05-devops.md", "hosting"),
    ("railway", "05-devops.md", "hosting"),
    ("netlify", "05-devops.md", "hosting"),
    ("https_ssl", "05-devops.md", "HTTPS"),
    ("https_ssl", "05-devops.md", "SSL"),
    ("https_ssl", "05-devops.md", "TLS"),
    ("health_check", "05-devops.md", "health"),

    # -- Security --
    ("cors", "06-security.md", "CORS"),
    ("rate_limiting", "06-security.md", "rate limit"),
    ("rate_limiting", "06-security.md", "Rate limit"),
    ("jwt", "06-security.md", "authentication"),
    ("jwt", "06-security.md", "JWT"),
    ("pydantic", "06-security.md", "input validation"),
    ("https_ssl", "06-security.md", "HTTPS"),
    ("https_ssl", "06-security.md", "TLS"),

    # -- Monitoring --
    ("sentry", "07-monitoring.md", "error tracking"),
    ("sentry", "07-monitoring.md", "Sentry"),
    ("structured_logging", "07-monitoring.md", "logging"),
    ("structured_logging", "07-monitoring.md", "Logging"),
    ("structured_logging", "07-monitoring.md", "structured"),
    ("health_check", "07-monitoring.md", "health"),

    # -- SEO --
    ("og_meta", "08-seo-marketing.md", "og:"),
    ("og_meta", "08-seo-marketing.md", "OG"),
    ("og_meta", "08-seo-marketing.md", "Open Graph"),
    ("robots_txt", "08-seo-marketing.md", "robots"),
    ("sitemap", "08-seo-marketing.md", "sitemap"),
    ("ga4", "08-seo-marketing.md", "analytics"),
    ("ga4", "08-seo-marketing.md", "Analytics"),
    ("ga4", "08-seo-marketing.md", "tracking"),

    # -- Legal --
    ("privacy_policy", "09-legal-compliance.md", "privacy"),
    ("privacy_policy", "09-legal-compliance.md", "Privacy"),
    ("terms_of_service", "09-legal-compliance.md", "terms"),
    ("terms_of_service", "09-legal-compliance.md", "Terms"),

    # -- Performance --
    ("typescript", "10-performance.md", "tree-shak"),
    ("typescript", "10-performance.md", "Tree-shak"),

    # -- Testing --
    ("vitest", "11-testing.md", "test runner"),
    ("vitest", "11-testing.md", "Choose test"),
    ("jest", "11-testing.md", "test runner"),
    ("jest", "11-testing.md", "Choose test"),
    ("playwright", "11-testing.md", "E2E"),
    ("playwright", "11-testing.md", "end-to-end"),
    ("cypress", "11-testing.md", "E2E"),
    ("cypress", "11-testing.md", "end-to-end"),
    ("pytest", "11-testing.md", "test runner"),

    # -- CI/CD --
    ("github_actions", "12-cicd.md", "CI platform"),
    ("github_actions", "12-cicd.md", "Choose CI"),

    # -- Email --
    ("resend", "13-email-notifications.md", "email provider"),
    ("resend", "13-email-notifications.md", "Choose"),
    ("sendgrid", "13-email-notifications.md", "email provider"),
    ("postmark", "13-email-notifications.md", "email provider"),
    ("nodemailer", "13-email-notifications.md", "email provider"),

    # -- Analytics --
    ("ga4", "14-analytics.md", "analytics platform"),
    ("ga4", "14-analytics.md", "Choose"),
    ("ga4", "14-analytics.md", "web analytics"),
    ("posthog", "14-analytics.md", "analytics platform"),
    ("posthog", "14-analytics.md", "Choose"),

    # -- Accessibility --
    ("radix", "15-accessibility.md", "semantic"),
    ("radix", "15-accessibility.md", "Semantic"),
]


# ---------------------------------------------------------------------------
# Scan engine
# ---------------------------------------------------------------------------


_CONDITION_IF = re.compile(r"^<!--\s*if:(\w+)\s*-->")
_CONDITION_ENDIF = re.compile(r"^<!--\s*endif\s*-->")


def run_scan(root: Path, flags: dict[str, bool] | None = None) -> dict:
    """Scan codebase and return detection results + auto-check counts.

    When *flags* is provided, items inside disabled ``<!-- if:flag -->``
    blocks are **not** auto-checked, preventing false-pass score inflation.
    """
    signals = _build_detectors(root)
    active = {k for k, v in signals.items() if v}

    # Group detections for display
    tech_stack: dict[str, list[str]] = {
        "Framework": [],
        "Language": [],
        "Database": [],
        "Auth": [],
        "Payment": [],
        "UI/CSS": [],
        "State": [],
        "Testing": [],
        "Hosting": [],
        "Email": [],
        "Monitoring": [],
        "CI/CD": [],
        "SEO": [],
        "Security": [],
    }

    _label_map = {
        "react": ("Framework", "React"),
        "nextjs": ("Framework", "Next.js"),
        "vue": ("Framework", "Vue"),
        "svelte": ("Framework", "Svelte"),
        "angular": ("Framework", "Angular"),
        "fastapi": ("Framework", "FastAPI"),
        "django": ("Framework", "Django"),
        "flask": ("Framework", "Flask"),
        "express": ("Framework", "Express"),
        "typescript": ("Language", "TypeScript"),
        "python": ("Language", "Python"),
        "tailwind": ("UI/CSS", "Tailwind CSS"),
        "shadcn": ("UI/CSS", "shadcn/ui"),
        "radix": ("UI/CSS", "Radix UI"),
        "tanstack_query": ("State", "TanStack Query"),
        "redux": ("State", "Redux"),
        "zustand": ("State", "Zustand"),
        "react_hook_form": ("State", "React Hook Form"),
        "zod": ("State", "Zod"),
        "pydantic": ("State", "Pydantic"),
        "react_router": ("Framework", "React Router"),
        "framer_motion": ("UI/CSS", "Framer Motion"),
        "supabase_auth": ("Auth", "Supabase Auth"),
        "firebase_auth": ("Auth", "Firebase Auth"),
        "auth0": ("Auth", "Auth0"),
        "clerk": ("Auth", "Clerk"),
        "nextauth": ("Auth", "NextAuth.js"),
        "postgresql": ("Database", "PostgreSQL"),
        "mongodb": ("Database", "MongoDB"),
        "mysql": ("Database", "MySQL"),
        "sqlite": ("Database", "SQLite"),
        "prisma": ("Database", "Prisma"),
        "drizzle": ("Database", "Drizzle"),
        "sqlalchemy": ("Database", "SQLAlchemy"),
        "typeorm": ("Database", "TypeORM"),
        "stripe": ("Payment", "Stripe"),
        "lemon_squeezy": ("Payment", "Lemon Squeezy"),
        "paddle": ("Payment", "Paddle"),
        "resend": ("Email", "Resend"),
        "sendgrid": ("Email", "SendGrid"),
        "postmark": ("Email", "Postmark"),
        "nodemailer": ("Email", "Nodemailer"),
        "sentry": ("Monitoring", "Sentry"),
        "posthog": ("Monitoring", "PostHog"),
        "vitest": ("Testing", "Vitest"),
        "jest": ("Testing", "Jest"),
        "playwright": ("Testing", "Playwright"),
        "cypress": ("Testing", "Cypress"),
        "pytest": ("Testing", "pytest"),
        "github_actions": ("CI/CD", "GitHub Actions"),
        "docker": ("CI/CD", "Docker"),
        "vercel": ("Hosting", "Vercel"),
        "railway": ("Hosting", "Railway"),
        "netlify": ("Hosting", "Netlify"),
        "robots_txt": ("SEO", "robots.txt"),
        "sitemap": ("SEO", "sitemap.xml"),
        "og_meta": ("SEO", "OG meta tags"),
        "ga4": ("SEO", "Google Analytics"),
        "cors": ("Security", "CORS"),
        "rate_limiting": ("Security", "Rate limiting"),
        "jwt": ("Security", "JWT auth"),
        "https_ssl": ("Security", "HTTPS/TLS"),
        "webhook_signature": ("Security", "Webhook signature verification"),
        "privacy_policy": ("SEO", "Privacy policy page"),
        "terms_of_service": ("SEO", "Terms of service page"),
        "structured_logging": ("Monitoring", "Structured logging"),
        "health_check": ("Monitoring", "Health check endpoint"),
    }

    for sig in active:
        if sig in _label_map:
            cat, label = _label_map[sig]
            if label not in tech_stack[cat]:
                tech_stack[cat].append(label)

    # Remove empty categories
    tech_stack = {k: v for k, v in tech_stack.items() if v}

    # --- Apply rules to blueprint files ---
    bp_dir = root / "docs" / "blueprints"
    checked_count: dict[str, int] = {}  # filename -> newly checked items
    total_newly_checked = 0

    _check_done_re = re.compile(r"^\s*-\s*\[x\]\s+", re.IGNORECASE)
    _check_todo_re = re.compile(r"^(\s*-\s*)\[\s\](\s+.+)$")

    # Group rules by blueprint
    rules_by_bp: dict[str, list[str]] = {}
    for signal, bp_file, substring in SCAN_RULES:
        if signal in active:
            rules_by_bp.setdefault(bp_file, []).append(substring)

    for bp_file, substrings in rules_by_bp.items():
        bp_path = bp_dir / bp_file
        text = _read(bp_path)
        if not text:
            continue

        lines = text.splitlines()
        newly_checked = 0
        condition_stack: list[bool] = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Track condition markers
            m_if = _CONDITION_IF.match(stripped)
            if m_if:
                flag_name = m_if.group(1)
                if flags is not None:
                    condition_stack.append(flags.get(flag_name, True))
                else:
                    condition_stack.append(True)
                continue
            if _CONDITION_ENDIF.match(stripped):
                if condition_stack:
                    condition_stack.pop()
                continue

            # Skip items in disabled condition blocks
            if condition_stack and not all(condition_stack):
                continue

            # Skip already-checked items
            if _check_done_re.match(line):
                continue
            m = _check_todo_re.match(line)
            if not m:
                continue
            item_text = m.group(2).lower()
            # Check if any substring matches
            for sub in substrings:
                if sub.lower() in item_text:
                    lines[i] = f"{m.group(1)}[x]{m.group(2)}"
                    newly_checked += 1
                    break  # Don't double-check same item

        if newly_checked > 0:
            out_text = "\n".join(lines)
            if text.endswith("\n"):
                out_text += "\n"
            bp_path.parent.mkdir(parents=True, exist_ok=True)
            bp_path.write_text(out_text, encoding="utf-8")
            checked_count[bp_file] = newly_checked
            total_newly_checked += newly_checked

    return {
        "tech_stack": tech_stack,
        "active_signals": sorted(active),
        "checked_count": checked_count,
        "total_newly_checked": total_newly_checked,
    }
