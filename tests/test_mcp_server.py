import asyncio
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mmu_cli import mcp_server  # noqa: E402


class MCPDataLayerTests(unittest.TestCase):
    def test_list_blueprints_returns_core_and_industry(self):
        blueprints = mcp_server.list_blueprints(REPO_ROOT)
        names = [b["name"] for b in blueprints]
        self.assertIn("01-frontend", names)
        self.assertIn("ai-product", names)
        self.assertTrue(len(blueprints) >= 17)
        for entry in blueprints:
            self.assertIn("path", entry)
            self.assertIn("description", entry)

    def test_get_blueprint_by_short_name(self):
        result = mcp_server.get_blueprint("frontend", REPO_ROOT)
        self.assertEqual(result["name"], "01-frontend")
        self.assertIn("Frontend", result["content"])

    def test_get_blueprint_industry(self):
        result = mcp_server.get_blueprint("ai-product", REPO_ROOT)
        self.assertEqual(result["name"], "ai-product")
        self.assertTrue(len(result["content"]) > 0)

    @mock.patch("mmu_cli.mcp_server._list_blueprint_files")
    def test_get_blueprint_collision_raises(self, mock_list):
        mock_list.return_value = [
            Path("/mock/01-billing.md"),
            Path("/mock/02-billing.md"),
        ]
        with self.assertRaises(ValueError) as ctx:
            mcp_server.get_blueprint("billing", REPO_ROOT)
        self.assertIn("Multiple blueprints matched 'billing'", str(ctx.exception))

    def test_get_blueprint_unknown_raises(self):
        with self.assertRaises(ValueError):
            mcp_server.get_blueprint("does-not-exist", REPO_ROOT)

    def test_list_idea_templates(self):
        templates = mcp_server.list_idea_templates(REPO_ROOT)
        names = [t["name"] for t in templates]
        self.assertIn("start", names)
        self.assertIn("close", names)
        self.assertIn("product-hunt", names)

    def test_validate_idea_runs_real_pipeline(self):
        calls = {}

        def fake_search_hn(query, limit=20):
            calls["hn"] = (query, limit)
            return [{"source": "hn", "title": "Great idea", "url": "https://hn.example", "text": "love it"}]

        def fake_search_reddit(query, limit=20):
            calls["reddit"] = (query, limit)
            return [{"source": "reddit", "title": "Bad idea", "url": "https://r.example", "text": "hate it"}]

        with (
            mock.patch("mmu_cli.mcp_server._missing_validate_extra", return_value=False),
            mock.patch("mmu_cli.validators.search_hn", fake_search_hn),
            mock.patch("mmu_cli.validators.search_reddit", fake_search_reddit),
            mock.patch(
                "mmu_cli.validators.analyze_sentiment",
                return_value={"compound": 0.5, "count": 2, "pos": 0.5, "neg": 0.1, "neu": 0.4},
            ),
            mock.patch("mmu_cli.validators.extract_competitors", return_value=[("Notion", 3)]),
        ):
            result = mcp_server.validate_idea("AI tutor for kids", limit=7)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["idea"], "AI tutor for kids")
        self.assertEqual(result["threads_found"], 2)
        self.assertEqual(result["verdict"], "POSITIVE LEAN")
        self.assertEqual(result["competitors"], [{"name": "Notion", "mentions": 3}])
        self.assertEqual(calls["hn"], ("AI tutor for kids", 7))
        self.assertEqual(calls["reddit"], ("AI tutor for kids", 7))
        self.assertEqual(len(result["top_threads"]), 2)

    def test_validate_idea_reports_error_when_both_sources_fail(self):
        def boom(query, limit=20):
            raise RuntimeError("network down")

        with (
            mock.patch("mmu_cli.mcp_server._missing_validate_extra", return_value=False),
            mock.patch("mmu_cli.validators.search_hn", boom),
            mock.patch("mmu_cli.validators.search_reddit", boom),
        ):
            result = mcp_server.validate_idea("AI tutor for kids")

        self.assertEqual(result["status"], "error")
        self.assertEqual(len(result["errors"]), 2)

    def test_validate_idea_unavailable_without_extra(self):
        with mock.patch("mmu_cli.mcp_server._missing_validate_extra", return_value=True):
            result = mcp_server.validate_idea("AI tutor for kids")
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("[validate]", result["note"])

    def test_resolve_repo_root_raises_when_explicit_root_invalid(self):
        path = Path("/nonexistent/path")
        with self.assertRaises(FileNotFoundError) as ctx:
            mcp_server._resolve_repo_root(path)
        self.assertIn(str(path), str(ctx.exception))

    def test_resolve_repo_root_uses_package_fallback_when_none(self):
        resolved = mcp_server._resolve_repo_root(None)
        self.assertEqual(resolved, REPO_ROOT)

    def test_rule_helpers(self):
        rules = mcp_server.list_rules()
        ids = [r["id"] for r in rules]
        self.assertIn("webhook-signature", ids)
        self.assertEqual(set(rules[0]), {"id", "title", "severity", "summary", "tags"})
        rule = mcp_server.explain_rule("secrets")
        self.assertEqual(rule["id"], "secrets")
        self.assertTrue(rule["fix"])
        with self.assertRaises(ValueError) as ctx:
            mcp_server.explain_rule("nope")
        self.assertIn("webhook-signature", str(ctx.exception))

    def test_vibecheck_tool_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "db.py").write_text('q = f"SELECT * FROM t WHERE id = {i}"\n', encoding="utf-8")
            doc, text = mcp_server.vibecheck_tool(tmp)
            self.assertEqual(json.loads(text), doc)
            doc2, agent = mcp_server.vibecheck_tool(tmp, format="agent")
            self.assertEqual(doc2["summary"], doc["summary"])
            self.assertIn("P0 sql-fstring db.py:1", agent)
            for kwargs, needle in [({"scope": "changed"}, "not-a-git-repo"), ({"scope": "bogus"}, "scope must be"),
                                   ({"format": "xml"}, "format must be")]:
                with self.assertRaises(ValueError) as ctx:
                    mcp_server.vibecheck_tool(tmp, **kwargs)
                self.assertIn(needle, str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            mcp_server.vibecheck_tool("/nonexistent/mmu/project")
        self.assertIn("not a directory", str(ctx.exception))


def _dump(obj):
    """SDK objects (v1 and v2) to plain camelCase JSON data."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(by_alias=True, mode="json")
    if isinstance(obj, (list, tuple)):
        return [_dump(o) for o in obj]
    return obj


@unittest.skipIf(mcp_server.sdk_major() is None, "mcp SDK not installed (install via [mcp] extra)")
class MCPServerTests(unittest.TestCase):
    """Runs against whichever SDK major is installed; CI runs it under mcp 1.x and 2.x."""

    def setUp(self):
        self.server = mcp_server.build_server(REPO_ROOT)

    def _call(self, name, args):
        return asyncio.run(self.server.call_tool(name, args))

    def test_sdk_major_matches_installed_package(self):
        from importlib.metadata import version
        self.assertEqual(mcp_server.sdk_major(), int(version("mcp").split(".")[0]))

    def test_tools_descriptions_and_annotations(self):
        tools = {t.name: _dump(t) for t in asyncio.run(self.server.list_tools())}
        self.assertEqual(list(tools)[0], "mmu_vibecheck")
        self.assertEqual(set(tools), {
            "mmu_vibecheck", "mmu_explain_rule", "mmu_list_rules", "mmu_validate_idea",
            "mmu_get_blueprint", "mmu_list_blueprints", "mmu_list_idea_templates",
        })
        for name, tool in tools.items():
            self.assertIn("Use when", tool["description"], f"{name} description must say when to use it")
            self.assertTrue(tool["title"], name)
            self.assertIs(tool["annotations"]["readOnlyHint"], True, name)
            self.assertIs(tool["annotations"]["openWorldHint"], name == "mmu_validate_idea", name)

    def test_vibecheck_output_schema_is_the_v1_document(self):
        tool = next(_dump(t) for t in asyncio.run(self.server.list_tools()) if t.name == "mmu_vibecheck")
        schema = tool["outputSchema"]
        self.assertEqual(set(schema["required"]), {"schema", "tool", "root", "scope", "summary", "findings"})
        self.assertIn("blocking", json.dumps(schema))
        self.assertIn("rule_id", json.dumps(schema))
        props = tool["inputSchema"]["properties"]
        self.assertEqual(set(props), {"project_root", "scope", "format"})

    def test_vibecheck_call_returns_structured_document_and_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "db.py").write_text('q = f"SELECT * FROM t WHERE id = {i}"\n', encoding="utf-8")
            for fmt in ("json", "agent"):
                out = _dump(self._call("mmu_vibecheck", {"project_root": tmp, "format": fmt}))
                doc = out["structuredContent"]
                self.assertEqual(doc["schema"], "mmu.vibecheck/v1")
                self.assertEqual(doc["summary"]["blocking"], 1)
                finding = next(f for f in doc["findings"] if f["rule_id"] == "sql-fstring")
                self.assertEqual(finding["locations"][0]["path"], "db.py")
                self.assertEqual(finding["locations"][0]["line"], 1)
                text = out["content"][0]["text"]
                if fmt == "agent":
                    self.assertIn("P0 sql-fstring db.py:1", text)
                else:
                    self.assertEqual(json.loads(text)["summary"], doc["summary"])

    def test_vibecheck_call_errors(self):
        for args, needle in [({"project_root": "/nonexistent/mmu/project"}, "not a directory"),
                             ({"project_root": str(REPO_ROOT), "scope": "bogus"}, "scope must be"),
                             ({"rule_id": "nope"}, "unknown rule id"), ({"name": "nope"}, "Blueprint not found")]:
            tool = "mmu_explain_rule" if "rule_id" in args else "mmu_get_blueprint" if "name" in args else "mmu_vibecheck"
            try:
                out = _dump(self._call(tool, args))
            except Exception as exc:  # v1 raises ToolError from call_tool
                self.assertIn(needle, str(exc))
            else:  # v2 returns an error result
                self.assertTrue(out.get("isError"), out)
                self.assertIn(needle, json.dumps(out))

    def test_rule_tools(self):
        self.assertIn("webhook-signature", json.dumps(_dump(self._call("mmu_list_rules", {}))))
        self.assertIn("ROW LEVEL SECURITY", json.dumps(_dump(self._call("mmu_explain_rule", {"rule_id": "supabase-rls"}))).upper())

    def test_build_server_fails_fast_on_invalid_root(self):
        path = Path("/nonexistent/mmu/root")
        with self.assertRaises(FileNotFoundError) as ctx:
            mcp_server.build_server(path)
        self.assertIn(str(path), str(ctx.exception))

    def test_stdio_handshake_reports_package_version_and_instructions(self):
        """Real process, real stdio transport: initialize, then tools/list."""
        from importlib.metadata import version
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
        env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
        proc = subprocess.Popen([sys.executable, "-m", "mmu_cli", "serve-mcp"], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        try:
            replies = {}
            for req in requests:
                proc.stdin.write(json.dumps(req) + "\n")
                proc.stdin.flush()
                if "id" in req:
                    msg = json.loads(proc.stdout.readline())
                    replies[msg["id"]] = msg
        finally:
            proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=10)
            proc.stdout.close()
            proc.stderr.close()
        info = replies[1]["result"]
        self.assertEqual(info["serverInfo"]["name"], "make-me-unicorn")
        self.assertEqual(info["serverInfo"]["version"], version("make-me-unicorn"))
        self.assertIn("mmu_vibecheck", info["instructions"])
        self.assertIn("before you commit", info["instructions"])
        self.assertEqual(len(replies[2]["result"]["tools"]), 7)


if __name__ == "__main__":
    unittest.main()
