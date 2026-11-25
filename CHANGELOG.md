# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and follows semantic intent.

## [Unreleased]

### Breaking

- **`mmu vibecheck` exit codes.** `0` = no blocking findings, `1` = blocking (P0) findings, `2` = usage/runtime error (bad `--root`, git unavailable for a scoped scan, unknown rule id). Blocking findings previously exited `2`; scripts that test for "non-zero" keep working, scripts that test for `== 2` must change.
- **`mmu vibecheck --json` output is now the `mmu.vibecheck/v1` document** (`docs/vibecheck-json-schema.md`): `schema`, `tool`, `root`, `scope`, `summary`, `findings`. The `messages` text blob, `failures` and `exit_code` keys are gone; `ok`/`skip` findings are listed only with `--all`. Findings keep `check`, `hint` and `files` as deprecated aliases next to `rule_id`, `fix` and `locations`.
- The `webhook-safety` skip finding is replaced by `webhook-signature` and `webhook-idempotency` skips, so every finding id is a registered rule.
- `mmu_vibecheck` MCP tool returns the same v1 document (was `{findings, failures, exit_code}`).

### Changed: `mmu vibecheck` rule accuracy

Measured on 12 fixtures and 20 open-source apps (`docs/benchmark.md`): P0 findings judged wrong on review went from 11 of 16 to 0 of 4 on the real-world sweep; fixtures score 100% P0 precision and recall.

- **Severity policy.** P0 = high confidence and launch-blocking. Findings about something being absent are P1. `password-reset` and `webhook-idempotency` are now P1. A `.env` that git does not ignore is P0 only when it holds a known key signature; other credential-named values are the new P1 `env-not-ignored`; placeholder values are not reported. `pickle.load(s)` is P0 when the input visibly comes from outside the process and P1 otherwise (unsafe YAML loaders stay P0).
- **Comments are not evidence.** A `// TODO: add sentry`, a "dedupe" comment or a commented-out `constructEvent` no longer satisfies a check; docstrings no longer trigger `debug-mode`.
- `password-reset` (P0 → P1): warns only when the app verifies passwords itself (`signInWithPassword`, bcrypt/argon2 verify, credentials providers, ...) and no forgot/reset flow exists anywhere in the project. No longer triggered by file names (`AuthorBio.tsx`), passwordless or OAuth-only apps, or projects on a managed auth product (Clerk, Auth0, Stytch, ...). Recognises `password_reset`, `password-reset`, `reset_password`.
- `webhook-signature` / `webhook-idempotency`: judged per handler, with evidence taken from the handler and the first-party helpers it imports. Handlers are found by route and content (`event.type`, provider event names), not only by file name; UI components and webhook-settings endpoints are not handlers. Recognises FastAPI `Header()`, `stripe.Webhook.construct_event`, `x-hub-signature-256`, Svix, `verifyWebhook`, HMAC comparisons; idempotency recognises `on_conflict_do_nothing` / `onConflictDoNothing` and warns only for effects that are wrong when repeated.
- `sql-fstring`: flags only strings shaped like a SQL statement with a value interpolated, reaching an execute-like call or written in upper-case SQL. `f"Update available: {v}"` is not SQL. Also covers `%` formatting, `.format()`, concatenation, and JS/TS template literals and concatenation passed to `query` / `execute` / `raw` / `$queryRawUnsafe`. Constant identifiers, generated placeholders and tagged templates are not flagged.
- `secrets`: also scans `.json`, `.yaml`, `.toml`, `.ini`, `.properties`, `.tf`, `.mjs`, `.cjs`, `Dockerfile*` and dotenv variants (`.env.production`, `prod.env`) that git does not ignore; skips lockfiles, templates and documentation placeholders (`sk_live_xxxx...`). A Supabase `service_role` JWT hardcoded in any source file is P0. Adds Stripe restricted/webhook, SendGrid and GitLab key signatures.
- `client-bundle-secrets`: server-only provider keys behind a public prefix (`NEXT_PUBLIC_OPENAI_API_KEY`).
- `rate-limiting`: `lodash.throttle`, the word "upstash" and `express` inside "expression" no longer count; an installed but unused limiter still warns; Cloudflare rate limit bindings are recognised.
- `cors-wildcard`: `cors()` with no options (Express, Hono, Fastify); the message says when a wildcard or reflected origin is combined with credentials.
- `debug-mode`: `app.run(debug=True)`, `FastAPI(debug=True)`, and dev servers (`--reload`, `npm run dev`) in a production Dockerfile `CMD`.
- `unsafe-deserialization`: `yaml.load(f, yaml.SafeLoader)` (positional loader) is safe.
- `error-monitoring` is skipped for projects without a server framework.
- `git-config-exec`: a `core.hooksPath` inside the repository or its git dir is not reported.
- **Fix text follows the framework** of the flagged file (Next.js, Express, Hono, FastAPI, Flask, Django, Supabase) instead of listing every variant. `--list-rules --format json` exposes `fix_variants`.

### Changed: what gets scanned

- **Breaking for projects that relied on it:** root `scripts/`, `tests/`, `docs/`, `examples/`, `cli/` and `src/mmu_cli` are no longer skipped. Those were excludes for this repository and hid user code. Defaults now skip only vendor and build directories at any depth (adds `vendor`, `target`, `out`, `.vercel`, `.output`, `.wrangler`, ...). Project-specific excludes go in `.mmu/config.toml` (`[vibecheck] skip_paths` or `[doctor] skip_paths`); this repository ships its own.
- Results no longer depend on directory order or project size: files are processed in path order and the 400-file caps are gone (files over 1 MB and minified bundles are skipped; a 20,000-file cut-off is reported in `scope.truncated`).
- `.gitignore` is honoured the way git does it (`git check-ignore` inside a work tree, a pattern matcher elsewhere): `/.env`, `.env*`, `*.env`, nested ignore files and `!` negations.
- Repo-level findings (`git-config-exec`, `env-not-ignored`, anything in a dotenv file) stay in the result under `--changed`, `--staged` and `--since`.

### Added

- **New rules.** `code-injection` (P0: `eval`, `new Function`, `child_process.exec`, `os.system`, `subprocess(..., shell=True)` with a request value in the same expression), `jwt-secret-default` (P0: signing secret assigned a literal or given a literal fallback, e.g. `os.getenv("JWT_SECRET", "dev")`, `process.env.SESSION_SECRET || "changeme"`), `env-not-ignored` (P1), `llm-route-unthrottled` (P1: a route calling a paid LLM SDK with no auth and no rate limit in the file or in middleware), `admin-route-no-auth` (P1), `dangerous-html` (P1: `dangerouslySetInnerHTML`, `v-html`, `innerHTML` with a non-literal value and no sanitizer), `stack-trace-leak` (P1: `traceback.format_exc()` / `err.stack` in an HTTP response without an environment guard).
- **Baseline for existing projects.** `mmu vibecheck --write-baseline [FILE]` records current findings (default `.mmu/vibecheck-baseline.json`); `--baseline [FILE]` reports them with status `baselined` (non-blocking, counted in `summary.baselined`) so only new findings block.
- **Benchmark.** `bench/` (fixtures with ground truth, no credentials committed), `scripts/bench.py`, `docs/benchmark.md`, and a test that fails on any P0 false positive or a drop in recall.
- **Vibecheck engine v2: an output contract built for coding agents.**
  - Every finding carries `locations` with `path`, `line` and a `snippet` (secret values redacted). Absence findings (no password reset, unverified webhook, no rate limiting, no error monitoring) anchor to the file that creates the obligation.
  - Rule registry: stable `rule_id`, title, summary, concrete `fix` instructions, `ref`, tags, confidence. `mmu vibecheck --list-rules` and `mmu vibecheck --explain <rule-id>`.
  - Suppressions: `mmu-ignore[<rule-id>]: <reason>` on the flagged line or alone on the line above (a marker without a reason is not applied), and `[vibecheck] ignore = ["rule-id", "path/glob/**:rule-id"]` in `.mmu/config.toml`. Suppressed findings are reported with status `suppressed` and counted in `summary.suppressed`.
  - Scoping for agent loops: `--changed` (tracked changes vs HEAD + untracked), `--staged`, `--since <ref>`. Without git or outside a repository these exit `2` instead of silently scanning everything.
  - `--format text|json|sarif|agent`, `--output <file>`, `--fail-on P0|P1|never`, `--all`. `agent` is compact plain text for LLM context; `sarif` is SARIF 2.1.0 for code-scanning upload. `mmu --json vibecheck` (flag before the subcommand) now works. With `--format json`, errors are a JSON object `{"schema", "error": {"code", "message"}}` on stdout.
  - GitHub Action inputs `format`, `sarif-file` and `fail-on`.
- **Four new `mmu vibecheck` rules grounded in field data.** Reeve's August 2026 scan of 30,998 live vibe-coded apps found 57% of Supabase-backed apps with unauthenticated table reads, 1 in 23 shipping a secret in the public bundle, and 13% publishing source maps — so: `client-bundle-secrets` (P0: `service_role` JWTs, known key signatures, or credential-named values behind `NEXT_PUBLIC_`/`VITE_`/`REACT_APP_`… prefixes, in `.env*` files and client code), `supabase-rls` (P0: tables created under `supabase/` without `ENABLE ROW LEVEL SECURITY`; P1 warn when Supabase is used but no SQL is in the repo), `sourcemaps-exposed` (P1: Vite/Next/webpack production source-map flags), and `git-config-exec` (P0: git config keys such as `core.fsmonitor` that run a command when an agent opens the repo — the GitSpawn class, Sep 2026; follows `gitdir:` pointers and `include.path`, ignores husky/git-lfs/`ssh` settings).
- **`ref` on findings** — every new rule prints a `why:` link to the incident report or dataset that motivated it. JSON output carries the same field.
- **Test/fixture downgrade** — a P0 whose offending files all live in test directories (`tests/`, `__tests__/`, `fixtures/`, …) or test-suffixed code files becomes a P1 warning instead of failing the build. Deliberately narrow: `examples/`, `mocks/`, Next.js `app/test/route.ts`, and dotfiles are not treated as tests.
- **Scanner prunes dependency/build directories at any depth** (`node_modules`, `.next`, `venv`, `site-packages`, …) and now includes `.mjs`/`.mts`/`.cjs`; `.env*`, build configs and `supabase/` are discovered up to three levels deep for monorepos.
- **Claude Code plugin now gates commits.** A PreToolUse hook (`hooks/vibecheck_gate.py`) runs `mmu vibecheck` before any `git commit` / `git push` the agent issues (including `git -C <path>`, env-prefixed, chained and subshell forms) and blocks on P0 findings, printing the finding, hint, and `why:` link to the agent. Uses the plugin's bundled source; if the scanner cannot run, the commit is allowed and a visible warning is shown instead of a silent pass. All subprocesses share a 45s deadline under the hook's 60s timeout. Bypass one command with a `MMU_HOOK_DISABLE=1` prefix, or set it in the environment to disable for the session; `MMU_HOOK_ON_PUSH_ONLY=1` gates only pushes.
- **`mmu_vibecheck` MCP tool** — the scanner is callable from any MCP client (findings, failure count, exit code). Rejects a `project_root` that is not a directory instead of returning a clean verdict for a path it never scanned.

### Changed

- `mmu_cli.vibecheck` is now a package (`engine`, `output`, `command`, `rules/`); existing imports (`check_*`, `Finding`, `run_vibecheck`, `format_findings`, `downgrade_test_only_findings`) are re-exported unchanged.
- The commit-gate hook reads the v1 document: the block reason lists `rule-id path:line` and the fix, and a scanner error (exit 2) allows the commit with a visible warning.
- Vibecheck text output shows `path:line` and the fix for each finding.
- MCP tool descriptions rewritten to state purpose, when to use, arguments and return shape (following the TDQS tool-definition guidance); `mmu_vibecheck` and `mmu_validate_idea` are listed first, and `mmu_validate_idea` now documents its real `status`/`top_threads` shape.
- Plugin manifest category `productivity` → `security`; description leads with the commit gate. FAQ, Product Hunt kit, `server.json`, and the four translated READMEs updated to match.
- CI lint and type-check now cover `hooks/`.

### Fixed

- `mmu init --force` no longer wipes progress: checklist templates are refreshed with checked items carried over, and edited docs and `.mmu/config.toml` are kept. Use the new `mmu init --reset` to overwrite everything.
- `mmu check` / `mmu uncheck` accept only an exact blueprint name or alias. Partial names (`e`, `latest`) used to modify an unrelated blueprint; they now fail with a suggestion. `mmu show` still accepts an unambiguous partial name and reports ambiguous ones.
- `mmu scan` no longer inflates the score: MMU's own scaffold (`docs/`, `prompts/`, `.mmu/`, `Unicorn.md`, `current_sprint.md`) and dependency/build directories are not evidence, markers that match almost any codebase (`G-`, `https://`, `ssl`, `logger`, `throttle`) are gone, and rules no longer tick items a marker cannot prove (forgot-password flow, CORS allowlist, webhook events). New `mmu scan --dry-run` lists what would be checked without writing.
- Badges for the 55–75% `young` stage render purple instead of gray.
- `mmu next` in a directory without blueprints says the project is not initialized instead of "you're done".
- `mmu validate` without the `[validate]` extra prints the install command instead of "Check your internet connection"; when one source fails, the report, markdown and JSON output (`errors`) say the results are partial.
- `mmu snapshot` exits `2` with an explanation when the snapshot script is absent (it is not shipped in the PyPI package).
- Default LLM model is `claude-sonnet-5-5` (override with `MMU_MODEL`).

## [0.7.0] - 2026-06-10

### Added

- **`mmu vibecheck`** — one-command scan for the gaps AI-generated code ships most: hardcoded secrets (Stripe/Anthropic/OpenAI/AWS/GitHub/Slack key signatures, unignored `.env`), webhook signature verification + idempotency, missing password-reset flow, f-string SQL, missing rate limiting, wildcard CORS, `DEBUG = True`, and absent error monitoring. P0 findings exit non-zero so it drops straight into CI. 14 new unit tests.
- **Blueprints, prompts, launch kit, and the TaskNote example are now bundled in the wheel** (`mmu_cli/data/`, kept in sync by `scripts/sync_packaged_data.py`; CI verifies with `--check`). `pip install make-me-unicorn` now gives a complete experience without a repo clone — previously `mmu init` silently skipped copying blueprints and `mmu serve-mcp` failed outright.
- **`mmu_validate_idea` MCP tool is now wired to the real validator** (was a stub). Agents get verdict, sentiment, candidate competitors, and top threads from live HN + Reddit search — free mode only; `--llm` synthesis stays CLI-only because it is a paid opt-in.
- `server.json` metadata for the official MCP Registry.
- Comparison table ("How is MMU different?") and hero/demo media in the English README; all five READMEs synced.
- **New demo GIF + reproducible demo pipeline** — `scripts/record_demo_cast.py` records real `mmu init → scan → vibecheck → dashboard` output against a fixture project; `scripts/render_cast_gif.py` renders the cast to GIF with Pillow. Regenerate any time with two commands.
- Release automation: pushing a `v*` tag now runs tests, builds distributions, and publishes a GitHub Release with notes extracted from this changelog (`.github/workflows/release.yml`).

### Changed

- **Validate reports no longer overwrite each other.** Reports are saved as `<slug>-<hash8>.md`, so repeat runs of the same idea reuse one file while distinct ideas that collide after slug truncation get distinct reports.
- HN + Reddit searches in `mmu validate` (and the MCP tool) run in parallel — roughly halves fetch latency.
- VADER verdict threshold (±0.2) is now a documented constant (`VERDICT_THRESHOLD`) with boundary tests; `verdict()` is public API.
- Competitor extraction stopwords expanded with ~80 common sentence-starters ("All", "Please", "Thanks", ...) that previously surfaced as fake competitor names.
- Checklist item counts corrected across all docs: 534+ → 670+ (574 core + 97 industry, verified by count).

### Fixed

- `LLMClient.complete()` now maps Anthropic API failures (auth, rate limit, connection, API errors) to friendly stderr messages and exit code 1 instead of raw tracebacks.
- Invalid `--root` paths fail fast with one clear error before any command logic runs.
- Corrupt `.mmu/config.toml` files now print a warning naming the file and the parse error instead of being silently ignored.
- Python 3.10: `get_api_key()` no longer crashes on `import tomllib` (3.11+ stdlib) — restored the tomllib/tomli fallback.
- MCP `mmu_validate_idea` without the `[validate]` extra returns a friendly "unavailable" payload instead of leaking an `ImportError` from sentiment analysis.
- `.gitignore` now covers nested validate reports (`reports/**/*.md`), so saved reports can't be committed accidentally.
- vibecheck: dict-form and assignment-form wildcard CORS origins are now detected; Next.js detection reuses `detect_nextjs()`; per-run file cache removes repeated reads across the 8 checks.

## [0.6.3] - 2026-05-08

### Fixed

- **`mmu serve-mcp` no longer crashes when called without `--root`.** The serve-mcp subparser sets `--root` default to `None` (so the MCP server can fall back to the package install location), but the shared dispatch in `main()` ran `root_path(None)` unconditionally — which raised `TypeError: argument should be a str ... not 'NoneType'`. `root_path()` now handles `None` by returning `Path.cwd()`. This was a latent regression in v0.6.0/0.6.1/0.6.2 — the published CLI's serve-mcp entry point was unusable without an explicit `--root`.
- 2 new unit tests (`test_root_path_handles_none`, `test_root_path_handles_string`) lock the contract.

### How it was caught

While building a demo GIF of `mmu serve-mcp` driven by an `mcp` Python SDK client, the server crashed at startup. The bug had slipped past three previous releases because every smoke test passed `--root` explicitly.

## [0.6.2] - 2026-05-07

### Fixed

- **`mmu serve-mcp` now actually fails fast on invalid `--root`.** v0.6.1 fixed `_resolve_repo_root` itself, but it was only called lazily inside each MCP tool function — so the server happily started up with a bad root and only errored once a client called a tool. `build_server` now validates the root once at startup, and `cli.py` translates the `FileNotFoundError` into a clean exit code 2 with the error message on stderr (no traceback).
- New unit test (`test_build_server_fails_fast_on_invalid_root`) skips gracefully when the `[mcp]` extra is absent.

## [0.6.1] - 2026-05-06

### Security

- **Prompt-injection defense in `mmu validate --llm`** — scraped Reddit/HN content is now wrapped in `<thread>` tags with sanitized close-tags, and the system prompt explicitly tells the model to treat thread content as data only. Reduces the surface for a hostile thread to override the validation prompt.

### Fixed

- **`mmu serve-mcp --root` now fails loudly on invalid paths.** Previously, an invalid `--root` silently fell back to the package install location, masking config mistakes. Explicit `--root` arguments must point at a checkout containing `docs/blueprints/`.
- **`mmu_validate_idea` MCP tool stub message** rewritten to clearly explain why MCP doesn't expose the full validator (network + LLM in stdio context) and direct users to the `mmu validate` CLI.
- **`mmu validate` no longer crashes on network errors.** HN or Reddit fetch failures are caught, reported on stderr, and the run continues with whatever data was retrieved. Both sources failing returns exit code 2 with a friendly message.

### Added

- 4 new unit tests (86 total) covering `_sanitize` and the explicit/None branches of `_resolve_repo_root`.

## [0.6.0] - 2026-05-06

### Added

- **Claude Code plugin packaging** (`.claude-plugin/`) — install MMU as a plugin via `/plugin marketplace add minjikim89/make-me-unicorn`. Compatible with Claude Code, Claude Desktop, and OpenAI Codex CLI (Anthropic Agent Skills spec, Dec 2025).
- **Agent Skill** (`skills/mmu-startup/`) — `SKILL.md` with auto-trigger phrases for "startup idea", "validate my idea", "launch checklist", and "Product Hunt prep". Uses progressive disclosure to load blueprints and the launch kit only when relevant.
- **MCP server mode** (`mmu serve-mcp`) — exposes MMU as a Model Context Protocol server so any MCP-compatible agent (Claude Code, Claude Desktop, Cursor, Gemini CLI) can call blueprints and templates as native tools. Tools: `mmu_list_blueprints`, `mmu_get_blueprint`, `mmu_list_idea_templates`, `mmu_validate_idea` (stub). Install with `pip install make-me-unicorn[mcp]`.
- New `[mcp]` optional-dependency group pinning `mcp>=1.27,<2`.
- **`mmu validate <idea>`** — pull real HN + Reddit discussions about a startup idea, compute local VADER sentiment, surface candidate competitors via capitalized-token NER. Saves markdown report to `reports/validate/<slug>.md`. Default mode is free (no API key, no paid calls).
- **`mmu validate --llm`** — opt-in Anthropic synthesis (verdict + pain points + competitors + risks + next experiments). Prompts for cost confirmation (~$0.05-0.20); use `--yes` / `-y` to skip.
- New `[validate]` optional-dependency group: `vaderSentiment>=3.3`, `requests>=2.28`. spaCy intentionally not used (heavy install; capitalized-token heuristic ships with v0.6, full NER planned for later).
- 10 new unit tests (75 total).
- 7 new unit tests for MCP server (82 total in main).

### Theme

v0.6 "Agent-Native" — extends v0.5's distribution thesis from human virality (badge/share) to agent virality (Skills marketplace + MCP registry). MMU is now installable as a Claude Code plugin and callable as an MCP server, so any LLM-backed agent can surface blueprints and validate ideas natively.

## [0.5.0] - 2026-04-12

### Added

- `mmu badge` — generate README badges in Markdown, SVG, or HTML format. Each badge links back to the project, creating organic growth through other READMEs.
- `mmu badge --format svg -o badge.svg` — save badge as local SVG file.
- `mmu badge --clipboard` — copy badge snippet to clipboard.
- **Stage-based badge colors** — badge color changes with unicorn stage (gray → orange → blue → purple → pink → gold).
- **Industry Blueprints** — new `docs/blueprints/industry/` directory with domain-specific checklists:
  - AI Product Blueprint (45+ items): model integration, cost control, prompt engineering, AI-specific UX, data privacy, ethical/legal.
  - Marketplace Blueprint (55+ items): supply/demand sides, transactions, trust & safety, marketplace economics.
- **Landing page** — Next.js Static Export website with interactive checklist demo, live score tracking, and unicorn stage evolution.
- GitHub Pages deployment workflow (`deploy-website.yml`).
- Product Hunt launch kit (`docs/launch/product-hunt.md`) with taglines, maker story, social templates, and success metrics.
- 7 new unit tests for badge generation (65 total, up from 58).

### Changed

- `mmu share` now includes GitHub URL and CTA line below the score card for better social sharing conversion.
- README restructured as distribution-first: demo → badge → share → problem → details (previously: problem → how it works → details).

## [0.4.0] - 2026-03-02

### Added

- `mmu share` — plain-text shareable score card with gate progress bars, stage name, stack info, and `#MakeMeUnicorn` hashtag.
- `mmu share --clipboard` — copy score card to clipboard (macOS).
- `mmu status --why` — Lighthouse-style score decomposition showing formula, per-blueprint breakdown, and skipped items.
- `mmu next [-n N]` — prioritized next-action recommendations with diversity cap (max 2 per blueprint).
- `mmu show <blueprint>` / `mmu check <blueprint> <#>` / `mmu uncheck` — drill-down and toggle individual checklist items.
- `mmu scan` — auto-detect tech stack and pre-check blueprint items.
- `mmu init` — baseline workspace scaffolding with stack selection (Next.js, Django, Rails, etc.) and `.mmu/config.toml` generation.
- `mmu init --interactive` — Claude-guided project setup (5 questions → 5 filled core docs).
- `mmu start --agent` — auto-format session context for direct LLM injection.
- `mmu doctor --deep` — semantic code review using Claude.
- `mmu generate <doc>` — generate or update core docs based on current project state.
- `mmu snapshot` — invoke snapshot diagnostics through the Python CLI.
- **Feature flag system** — `.mmu/config.toml` with 17 flags across features/architecture/market sections. Condition markers (`<!-- if:flag -->` / `<!-- endif -->`) in blueprints skip non-applicable items.
- **Visual status dashboard** with unicorn evolution art (Egg → Legendary).
- **Priority system** `[P0]`/`[P1]`/`[P2]` for blueprint items.
- **Full-Stack SaaS Blueprint** — 15 checklists, 400+ items covering frontend through accessibility.
- **LLM integration module** (`src/mmu_cli/llm.py`) — optional Claude-powered features via `pip install make-me-unicorn[llm]`.
- Multi-language READMEs: KO, JA, ZH-CN, ES.
- CLI demo GIF and 60-second quickstart in all READMEs.
- "Share your score" section in all READMEs.
- 58 unit tests (up from 24 in v0.3.0).

### Changed

- `prompts/close.md` — restructured with `[DONE]/[DECISION]/[ISSUE]/[NEXT]` memory tags.
- `prompts/start.md` — added Forbidden Patterns section and known_issues reference.
- `pyproject.toml` — added `[llm]` optional dependency group.
- Score calculation now excludes items in disabled feature flag sections (no more false-pass).
- `show`/`check` item numbering is condition-aware — hidden items don't shift visible numbers.

### Fixed

- `lstrip("[ ] ")` priority parsing bug → replaced with `re.sub()`.
- `next -n 0` no longer shows false "all done" (defaults to 3).
- Show/check item numbering mismatch when condition markers are active.
- Diversity cap remaining count uses actual selected count.
- `snapshot.sh` now parses `.snapshotrc` safely instead of sourcing arbitrary shell code.

## [0.3.0] - 2026-02-23

### Added

- Installable Python CLI command (`mmu`) via `pyproject.toml`.
- `start --emit bundle`, `--output`, and `--clipboard` options.
- JSON output mode (`--json`) for all commands.
- Unit test suite under `tests/`.
- CI lint/typecheck/tests in `.github/workflows/mmu-guardrails.yml`.
- Community files: `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue/PR templates.

### Changed

- `gate` parsing now supports flexible heading spacing and indented unchecked items.
- Stage format supports `M<number>` dynamically (for example `M6`).
- `doctor` now reports read failures instead of silently swallowing all file IO errors.
- Code scanning uses pruned directory walking and configurable skip paths via `.mmu/config.toml`.

### Fixed

- CI gate-target parsing bug that merged multiple stages into one token.

## [0.2.0] - 2026-02-23

### Added

- Initial founder OS docs and mode playbook.
- `mmu` prototype commands: `start`, `close`, `doctor`, `gate`.
- Guardrail workflow scaffold.
