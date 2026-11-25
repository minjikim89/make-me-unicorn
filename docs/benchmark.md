# `mmu vibecheck` benchmark

Two measurements, both reproducible from this repository:

1. **Fixture benchmark** – small projects with known planted issues and known-correct code. Measures recall and precision against a written ground truth.
2. **Real-world sweep** – popular open-source apps scanned as they are. Measures how often a P0 (blocking) finding is wrong on code the rules were not written against.

Severity policy the numbers are judged by: **P0** = high confidence and launch-blocking (exit code 1), **P1** = warning, including every heuristic about something being absent.

## 1. Fixture benchmark

Fixtures live in `bench/fixtures/`, ground truth in `bench/expected/<fixture>.toml`, the runner in `scripts/bench.py`.

Scoring is strict:

- every reported `(rule, path, severity)` that the ground truth does not list is a **false positive**;
- every listed one that is not reported (or is reported on a different line when the ground truth pins a line) is a **false negative**;
- planted issues that no rule targets are listed as `[[uncovered]]` and count as misses in "planted issues detected".

<!-- bench:fixtures:begin -->
12 fixtures. Regenerate with `python scripts/bench.py --markdown`.

| Metric | Value |
|--------|-------|
| P0 precision | 100% (29 true positives, 0 false positives) |
| P0 recall | 100% (29 of 29 expected P0 findings) |
| P1 precision | 97% (33 true positives, 1 false positives) |
| P1 recall | 100% (33 of 33 expected P1 findings) |
| Planted issues detected | 52 of 55 (95%), including issues no rule targets |
| `must_not` entries reported | 0 |

### Per rule

| Rule | TP | FP | FN |
|------|----|----|----|
| `admin-route-no-auth` | 2 | 0 | 0 |
| `client-bundle-secrets` | 3 | 0 | 0 |
| `code-injection` | 3 | 0 | 0 |
| `cors-wildcard` | 3 | 0 | 0 |
| `dangerous-html` | 2 | 0 | 0 |
| `debug-mode` | 3 | 0 | 0 |
| `disabled-ssl` | 1 | 0 | 0 |
| `env-not-ignored` | 3 | 0 | 0 |
| `error-monitoring` | 5 | 0 | 0 |
| `git-config-exec` | 1 | 0 | 0 |
| `jwt-localstorage` | 1 | 0 | 0 |
| `jwt-secret-default` | 3 | 0 | 0 |
| `llm-route-unthrottled` | 1 | 0 | 0 |
| `password-reset` | 3 | 0 | 0 |
| `rate-limiting` | 4 | 0 | 0 |
| `secrets` | 8 | 0 | 0 |
| `sourcemaps-exposed` | 1 | 0 | 0 |
| `sql-fstring` | 3 | 0 | 0 |
| `stack-trace-leak` | 3 | 0 | 0 |
| `supabase-rls` | 3 | 0 | 0 |
| `unsafe-deserialization` | 3 | 1 | 0 |
| `webhook-idempotency` | 1 | 0 | 0 |
| `webhook-signature` | 2 | 0 | 0 |

### Per fixture

| Fixture | TP | FP | FN | Planted issues detected | Missed |
|---------|----|----|----|-------------------------|--------|
| `agent-trap` | 1 | 0 | 0 | 2 of 2 | none |
| `express-bad` | 12 | 0 | 0 | 11 of 13 | C12, C13 |
| `express-good` | 0 | 0 | 0 | 0 of 0 | none |
| `fastapi-good` | 0 | 1 | 0 | 0 of 0 | none |
| `fastapi-sqlalchemy-openai` | 12 | 0 | 0 | 10 of 11 | B8 |
| `flask-legacy` | 12 | 0 | 0 | 11 of 11 | none |
| `hono-worker` | 2 | 0 | 0 | 1 of 1 | none |
| `next-good` | 2 | 0 | 0 | 0 of 0 | none |
| `next-supabase-good` | 0 | 0 | 0 | 0 of 0 | none |
| `next-supabase-stripe` | 12 | 0 | 0 | 8 of 8 | none |
| `py-venv` | 0 | 0 | 0 | 0 of 0 | none |
| `vite-express-leaky` | 9 | 0 | 0 | 9 of 9 | none |
<!-- bench:fixtures:end -->

### Fixtures

| Fixture | Contents |
|---------|----------|
| `next-supabase-stripe` | Next.js + Supabase + Stripe SaaS, 8 planted issues, 5 correct counterparts |
| `fastapi-sqlalchemy-openai` | FastAPI + SQLAlchemy + OpenAI API, 11 planted issues, 5 correct counterparts |
| `express-bad` | Express API with interpolated SQL, `eval` on request data, unverified webhook, keys in JSON/`.mjs`/`.env.production` |
| `flask-legacy` | Single-file Flask app: unsafe YAML loader, `eval`, `%`-formatted SQL, secret fallback, debug server, next to their safe forms |
| `vite-express-leaky` | Vue/Vite + Express: public-prefixed secret, source maps, token in localStorage, `v-html`, verified but non-idempotent webhook |
| `agent-trap` | `.git/config` with command-executing keys |
| `hono-worker` | Hono on Cloudflare Workers with a rate limit binding and default `cors()` |
| `next-good` | Correct passwordless Next.js + Supabase + Stripe app |
| `next-supabase-good` | Correct Next.js + Supabase + Stripe app with password login, reset flow, RLS, verified webhook; must scan clean |
| `express-good` | Correct Express API; must scan clean |
| `fastapi-good` | Correct FastAPI service; no P0 allowed |
| `py-venv` | Project with a virtualenv next to it; nothing under `venv/` may be reported |

### Known misses and limits

- `B8` (IDOR: a note is returned without an ownership check), `C12` (plaintext password comparison) and `C13` (login returns the password column) are not detected. No rule models data-flow or authorization logic.
- `fastapi-good` gets one P1 warning for `pickle.load` on a cache file the app wrote itself. The rule cannot see where the file comes from, so it warns instead of blocking.
- The fixtures were written by the same people as the rules, and several rules were tuned until these fixtures passed. Treat the fixture numbers as a regression suite, not as an estimate of accuracy on unseen code. The sweep below is the independent check.

### No credentials in the repository

Fixture files contain placeholders such as `{{SECRET:stripe_live}}`. `bench/materialize.py` copies a fixture to a temporary directory, replaces each placeholder with a synthetic value of the right shape, and renames `_dot_env` to `.env` (and `_dot_git/` to `.git/`) before the scan. The values are generated at run time and were never issued by any provider.

### Reproduce

```bash
pip install -e '.[dev]'
python scripts/bench.py              # tables on stdout
python scripts/bench.py --markdown   # rewrite the generated section above
python -m unittest tests.test_bench  # the gate: zero P0 false positives, recall not below the locked values
```

## 2. Real-world sweep

20 public repositories, shallow-cloned at the commits below and scanned with default settings (no config file, no suppressions). "Before" is the rule set at commit `430b07d` of this repository; "after" is the current one.

Triage was done by one reviewer reading the code each P0 points at. A match is counted as correct when the code does what the rule describes; that is a statement about a rule matching, not an assessment of the project. Most of these repositories are starters, tutorials and examples whose authors chose their scope on purpose.

| Result | Before | After |
|--------|--------|-------|
| Repositories with at least one P0 | 14 of 20 | 8 of 20 |
| P0 findings | 16 | 10 |
| P0 findings judged wrong on review | 11 | 0 |
| P0 findings where the code matches the rule | 5 | 10 |

| Repository | Commit | Files scanned | P0 before → after | P1 before → after | Scan time |
|------------|--------|---------------|-------------------|-------------------|-----------|
| `boxyhq/saas-starter-kit` | `abc9b68682` | 296 | 1 → 0 | 1 → 1 | 120 ms |
| `ChatGPTNextWeb/NextChat` | `1d3dc33151` | 211 | 1 → 0 | 1 → 3 | 405 ms |
| `expressjs/express` | `43fca52d28` | 152 | 0 → 1 | 3 → 0 | 80 ms |
| `fastapi-users/fastapi-users` | `e9c57ff7ff` | 93 | 1 → 0 | 2 → 3 | 100 ms |
| `fastapi/full-stack-fastapi-template` | `77e550a73b` | 187 | 1 → 0 | 2 → 2 | 130 ms |
| `gothinkster/node-express-realworld-example-app` | `30b68e1e88` | 52 | 1 → 2 | 2 → 3 | 19 ms |
| `hagopj13/node-express-boilerplate` | `179ae84efe` | 62 | 0 → 0 | 1 → 2 | 26 ms |
| `honojs/examples` | `3b0b62875a` | 76 | 1 → 0 | 1 → 2 | 191 ms |
| `ixartz/SaaS-Boilerplate` | `e3952a7ed5` | 107 | 2 → 0 | 1 → 0 | 60 ms |
| `KolbySisk/next-supabase-stripe-starter` | `9839fd47d2` | 62 | 1 → 0 | 2 → 2 | 36 ms |
| `mckaywrigley/chatbot-ui` | `81328b61d2` | 271 | 0 → 0 | 1 → 1 | 170 ms |
| `miguelgrinberg/microblog` | `a975ef6486` | 58 | 0 → 1 | 2 → 2 | 37 ms |
| `nextjs/saas-starter` | `6e33e58b1e` | 47 | 2 → 1 | 2 → 2 | 38 ms |
| `nsidnev/fastapi-realworld-example-app` | `029eb7781c` | 102 | 1 → 1 | 2 → 2 | 50 ms |
| `pallets/flask` | `49943b5a94` | 114 | 1 → 2 | 3 → 2 | 251 ms |
| `sahat/hackathon-starter` | `42fb2beaa5` | 88 | 1 → 0 | 1 → 1 | 154 ms |
| `umami-software/umami` | `dbb8d606fb` | 1699 | 1 → 1 | 2 → 1 | 1089 ms |
| `vercel/ai-chatbot` | `a8989b522f` | 163 | 1 → 1 | 0 → 1 | 99 ms |
| `vercel/nextjs-subscription-payments` | `bdd0813206` | 63 | 0 → 0 | 2 → 2 | 37 ms |
| `w3cj/hono-open-api-starter` | `0d5f3bf523` | 24 | 0 → 0 | 2 → 2 | 37 ms |

### Remaining P0 findings

| Repository | Finding |
|------------|---------|
| `expressjs/express` | matched rule `jwt-secret-default` at `examples/auth/index.js:22`, `examples/mvc/index.js:40`, `examples/session/index.js:16`, `examples/session/redis.js:20` (note 1) |
| `gothinkster/node-express-realworld-example-app` | matched rule `password-reset` at `src/app/routes/auth/auth.service.ts:111` (note 2) |
| `gothinkster/node-express-realworld-example-app` | 1 finding withheld pending maintainer contact |
| `miguelgrinberg/microblog` | 1 finding withheld pending maintainer contact |
| `nextjs/saas-starter` | matched rule `password-reset` at `app/(login)/actions.ts:76` (note 2) |
| `nsidnev/fastapi-realworld-example-app` | matched rule `password-reset` at `app/api/routes/authentication.py:38` (note 2) |
| `pallets/flask` | matched rule `jwt-secret-default` at `examples/tutorial/flaskr/__init__.py:11` (note 1) |
| `pallets/flask` | matched rule `password-reset` at `examples/tutorial/flaskr/auth.py:98` (note 2) |
| `umami-software/umami` | matched rule `password-reset` at `src/app/api/auth/login/route.ts:27` (note 2) |
| `vercel/ai-chatbot` | matched rule `password-reset` at `app/(auth)/auth.ts:59` (note 2) |

Note 1: example applications shipped inside a framework repository. The session secret is a literal placeholder in sample code, which is what the rule looks for; it says nothing about the framework itself.

Note 2: the repository verifies passwords itself and contains no forgot/reset-password flow. For a starter, a tutorial, a spec implementation or a self-hosted tool without outbound email that is a scope decision; the rule reports it because an app built on top inherits the gap.

### What changed between the two columns

The 11 P0 findings that review judged wrong all came from three causes, each fixed in the rules:

| Cause (before) | Findings | Rule now |
|----------------|----------|----------|
| `password-reset` fired on file names containing `auth`, `session`, `login` or `account` (passwordless apps, managed auth, a session model, a framework's session module, projects that do have a reset flow) | 7 | fires only when the code verifies a password itself and no reset flow exists anywhere; skips when a managed auth product owns recovery |
| `secrets` fired on any `.env` not listed literally in `.gitignore`, whatever it held (placeholder and public values) | 2 | P0 only for a known key signature or a `service_role` JWT in a file git does not ignore; other credential-named values are a P1 (`env-not-ignored`) |
| `webhook-idempotency` was P0 and fired on UI components in a `webhook/` folder and on handlers whose only effect is a status update | 2 | P1; handlers are routes that receive provider events; warns only for effects that are wrong when repeated |

New P0 matches in the "after" column come from rules that did not exist before (`jwt-secret-default`) and from `password-reset` now pointing at the line that verifies the password instead of at file names.

### Performance

Wall time of the scan itself (median of 3 runs, Python 3.12, Apple silicon laptop):

| Measure | Value |
|---------|-------|
| Median across the 20 repositories | 89 ms |
| Largest repository (`umami-software/umami`, 1,699 files scanned) | 1.09 s |
| Same repository through the CLI, including interpreter start (`mmu vibecheck --format json`) | 1.2 s |

### Reproduce

```bash
git clone --depth 1 https://github.com/<owner>/<repo> /tmp/sweep/<repo>
git -C /tmp/sweep/<repo> checkout <commit>     # after `git fetch --depth 1 origin <commit>` if it has moved
mmu vibecheck --root /tmp/sweep/<repo> --format json
```
