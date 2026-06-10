import sys
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
        with self.assertRaises(FileNotFoundError) as ctx:
            mcp_server._resolve_repo_root(Path("/nonexistent/path"))
        self.assertIn("/nonexistent/path", str(ctx.exception))

    def test_resolve_repo_root_uses_package_fallback_when_none(self):
        resolved = mcp_server._resolve_repo_root(None)
        self.assertEqual(resolved, REPO_ROOT)

    def test_build_server_fails_fast_on_invalid_root(self):
        try:
            import mcp.server.fastmcp  # noqa: F401
        except ImportError:
            self.skipTest("mcp SDK not installed (install via [mcp] extra)")
        with self.assertRaises(FileNotFoundError) as ctx:
            mcp_server.build_server(Path("/nonexistent/mmu/root"))
        self.assertIn("/nonexistent/mmu/root", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
