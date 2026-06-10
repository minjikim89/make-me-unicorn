import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mmu_cli import _data  # noqa: E402


class PackagedDataSyncTests(unittest.TestCase):
    def test_packaged_data_in_sync_with_canonical_sources(self):
        """Wheel data under src/mmu_cli/data must mirror docs/, prompts/, examples/."""
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "sync_packaged_data.py"), "--check"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

    def test_packaged_data_root_contains_blueprints(self):
        data_root = _data.packaged_data_root()
        self.assertIsNotNone(data_root)
        assert data_root is not None
        blueprints = list((data_root / "docs" / "blueprints").glob("*.md"))
        self.assertGreaterEqual(len([b for b in blueprints if b.name != "README.md"]), 15)
        self.assertTrue((data_root / "prompts" / "start.md").is_file())
        self.assertTrue((data_root / "docs" / "launch" / "product-hunt.md").is_file())
        self.assertTrue(
            (data_root / "examples" / "filled" / "tasknote" / "docs" / "core" / "strategy.md").is_file()
        )

    def test_find_content_root_prefers_checkout(self):
        # Running from the repo, the checkout (with the full docs tree) wins.
        self.assertEqual(_data.find_content_root(), REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
