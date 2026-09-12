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

    def test_flags_yaml_load_all_without_safe_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/config.py", "import yaml\nconfigs = yaml.load_all(raw_config)\n")
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("yaml.load_all without SafeLoader", finding.message)

    def test_flags_yaml_module_alias_load_all_without_safe_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/config.py", "import yaml as y\nconfigs = y.load_all(raw_config)\n")
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("yaml.load_all without SafeLoader", finding.message)

    def test_flags_yaml_unsafe_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/config.py", "import yaml\nconfig = yaml.unsafe_load(raw_config)\n")
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("yaml.unsafe_load", finding.message)

    def test_flags_yaml_full_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/config.py", "import yaml\nconfig = yaml.full_load(raw_config)\n")
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("yaml.full_load", finding.message)

    def test_flags_yaml_module_alias_convenience_loaders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "src/config.py",
                "import yaml as y\nfirst = y.unsafe_load(raw)\nsecond = consume(y.full_load(stream.read()))\n",
            )
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("yaml.unsafe_load", finding.message)
            self.assertIn("yaml.full_load", finding.message)

    def test_flags_imported_yaml_convenience_loader_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "src/config.py",
                "from yaml import unsafe_load\nfrom yaml import full_load as load_yaml\n"
                "first = unsafe_load(raw)\nsecond = load_yaml(raw)\n",
            )
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("yaml.unsafe_load", finding.message)
            self.assertIn("yaml.full_load", finding.message)

    def test_flags_yaml_all_document_convenience_loaders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "src/config.py",
                "import yaml as y\nfirst = y.unsafe_load_all(raw)\nsecond = y.full_load_all(raw)\n",
            )
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("yaml.unsafe_load_all", finding.message)
            self.assertIn("yaml.full_load_all", finding.message)

    def test_flags_imported_yaml_all_document_loader_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "src/config.py",
                "from yaml import unsafe_load_all\nfrom yaml import full_load_all as load_all_yaml\n"
                "first = unsafe_load_all(raw)\nsecond = load_all_yaml(raw)\n",
            )
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("yaml.unsafe_load_all", finding.message)
            self.assertIn("yaml.full_load_all", finding.message)

    def test_keeps_flagging_imported_yaml_load_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/config.py", "from yaml import load as load_yaml\nconfig = load_yaml(raw)\n")
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("yaml.load without SafeLoader", finding.message)

    def test_flags_imported_yaml_load_all_alias_without_safe_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/config.py", "from yaml import load_all as load_yaml\nconfigs = load_yaml(raw)\n")
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "fail")
            self.assertIn("yaml.load_all without SafeLoader", finding.message)

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

    def test_ok_for_yaml_load_with_csafe_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src/config.py", "import yaml\nconfig = yaml.load(raw, Loader=yaml.CSafeLoader)\n")
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "ok")

    def test_ok_for_yaml_load_all_with_safe_loaders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "src/config.py",
                "import yaml\nfirst = yaml.load_all(raw, Loader=yaml.SafeLoader)\n"
                "second = yaml.load_all(raw, Loader=yaml.CSafeLoader)\n",
            )
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "ok")

    def test_ok_for_imported_yaml_load_all_alias_with_safe_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "src/config.py",
                "from yaml import load_all as load_yaml\nfrom yaml import SafeLoader\n"
                "configs = load_yaml(raw, Loader=SafeLoader)\n",
            )
            finding = vibecheck.check_unsafe_deserialization(root, [root / "src/config.py"])
            self.assertEqual(finding.status, "ok")

    def test_ignores_unrelated_convenience_loader_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "src/config.py",
                "from data_tools import full_load as load_yaml\n"
                "from data_tools import full_load_all as load_all_yaml\n"
                "def unsafe_load(value): return value\n"
                "def unsafe_load_all(value): return value\n"
                "def load_all(value): return value\n"
                "first = load_yaml(raw)\nsecond = load_all_yaml(raw)\n"
                "third = unsafe_load(raw)\nfourth = unsafe_load_all(raw)\nfifth = load_all(raw)\n",
            )
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


if __name__ == "__main__":
    unittest.main()
