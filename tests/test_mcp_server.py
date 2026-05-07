import sys
import unittest
from pathlib import Path

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

    def test_validate_idea_stub(self):
        result = mcp_server.validate_idea("AI tutor for kids")
        self.assertEqual(result["status"], "stub")
        self.assertEqual(result["idea"], "AI tutor for kids")
        self.assertIn("mmu validate", result["note"])

    def test_resolve_repo_root_raises_when_explicit_root_invalid(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            mcp_server._resolve_repo_root(Path("/nonexistent/path"))
        self.assertIn("/nonexistent/path", str(ctx.exception))

    def test_resolve_repo_root_uses_package_fallback_when_none(self):
        resolved = mcp_server._resolve_repo_root(None)
        self.assertEqual(resolved, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
