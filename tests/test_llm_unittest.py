import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


class RequireLLMTest(unittest.TestCase):
    """Test that require_llm() gates properly."""

    def test_exits_when_sdk_missing(self) -> None:
        from mmu_cli import llm

        original = llm._HAS_ANTHROPIC
        try:
            llm._HAS_ANTHROPIC = False
            with self.assertRaises(SystemExit):
                llm.require_llm()
        finally:
            llm._HAS_ANTHROPIC = original

    def test_passes_when_sdk_available(self) -> None:
        from mmu_cli import llm

        original = llm._HAS_ANTHROPIC
        try:
            llm._HAS_ANTHROPIC = True
            llm.require_llm()  # should not raise
        finally:
            llm._HAS_ANTHROPIC = original


class GetApiKeyTest(unittest.TestCase):
    """Test API key resolution order."""

    def test_reads_mmu_env_var(self) -> None:
        from mmu_cli import llm

        with patch.dict(os.environ, {"MMU_ANTHROPIC_API_KEY": "test-key-mmu"}, clear=False):
            key = llm.get_api_key()
            self.assertEqual(key, "test-key-mmu")

    def test_reads_anthropic_env_var_fallback(self) -> None:
        from mmu_cli import llm

        env = {"ANTHROPIC_API_KEY": "test-key-anthropic"}
        with patch.dict(os.environ, env, clear=False):
            # Remove MMU-specific key if present
            os.environ.pop("MMU_ANTHROPIC_API_KEY", None)
            key = llm.get_api_key()
            self.assertEqual(key, "test-key-anthropic")

    def test_exits_when_no_key(self) -> None:
        from mmu_cli import llm

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                llm.get_api_key()


class FormatAgentContextTest(unittest.TestCase):
    """Test agent context formatting."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, rel: str, content: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_includes_mode_and_bundle(self) -> None:
        from mmu_cli.llm import format_agent_context

        self.write("prompts/start.md", "# Start\ntest prompt")
        self.write("current_sprint.md", "# Sprint\ngoal 1")

        result = format_agent_context("backend", "## bundle content", self.root)
        self.assertIn("Mode: backend", result)
        self.assertIn("bundle content", result)
        self.assertIn("test prompt", result)
        self.assertIn("goal 1", result)

    def test_works_without_optional_files(self) -> None:
        from mmu_cli.llm import format_agent_context

        result = format_agent_context("frontend", "bundle", self.root)
        self.assertIn("Mode: frontend", result)
        self.assertIn("bundle", result)


class InteractiveQuestionsTest(unittest.TestCase):
    """Test interactive questions parsing."""

    def test_collects_answers(self) -> None:
        from mmu_cli.llm import interactive_questions

        inputs = ["My SaaS app", "Solo founders", "Task management", "Next.js + Supabase", "Freemium"]
        with patch("builtins.input", side_effect=inputs):
            answers = interactive_questions()
        self.assertEqual(len(answers), 5)
        self.assertEqual(answers["Product"], "My SaaS app")
        self.assertEqual(answers["Stack"], "Next.js + Supabase")

    def test_skips_empty_answers(self) -> None:
        from mmu_cli.llm import interactive_questions

        inputs = ["My SaaS app", "", "Task management", "", "Freemium"]
        with patch("builtins.input", side_effect=inputs):
            answers = interactive_questions()
        self.assertEqual(len(answers), 3)
        self.assertNotIn("Customer", answers)


class LLMClientMockTest(unittest.TestCase):
    """Test LLMClient with mocked Anthropic SDK."""

    def _make_mock_anthropic(self, text: str = "Generated content", input_tokens: int = 100, output_tokens: int = 50) -> MagicMock:
        mock_mod = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=text)]
        mock_response.usage.input_tokens = input_tokens
        mock_response.usage.output_tokens = output_tokens
        mock_mod.Anthropic.return_value.messages.create.return_value = mock_response
        return mock_mod

    def test_complete_returns_text(self) -> None:
        from mmu_cli import llm

        original = llm._HAS_ANTHROPIC
        try:
            llm._HAS_ANTHROPIC = True
            mock_mod = self._make_mock_anthropic("Generated content", 100, 50)

            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                with patch.object(llm, "anthropic", mock_mod, create=True):
                    client = llm.LLMClient()
                    result = client.complete("system", "user")

            self.assertEqual(result, "Generated content")
            self.assertEqual(len(client.usage_log), 1)
            self.assertEqual(client.usage_log[0]["input_tokens"], 100)
        finally:
            llm._HAS_ANTHROPIC = original

    def test_log_usage_writes_file(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)

        from mmu_cli import llm

        original = llm._HAS_ANTHROPIC
        try:
            llm._HAS_ANTHROPIC = True
            mock_mod = self._make_mock_anthropic("test", 10, 5)

            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                with patch.object(llm, "anthropic", mock_mod, create=True):
                    client = llm.LLMClient(root)
                    client.complete("sys", "usr")
                    client.log_usage(root)

            log_path = root / ".mmu" / "llm_usage.log"
            self.assertTrue(log_path.is_file())
            content = log_path.read_text(encoding="utf-8")
            self.assertIn('"input_tokens": 10', content)
        finally:
            llm._HAS_ANTHROPIC = original
            tmp.cleanup()


class CLIStartAgentTest(unittest.TestCase):
    """Test --agent flag in start command."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, rel: str, content: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_agent_flag_outputs_structured_context(self) -> None:
        from mmu_cli import cli

        self.write("docs/core/product.md", "# Product\nhello")
        self.write("docs/ops/roadmap.md", "# Roadmap\nworld")
        self.write("prompts/start.md", "# Start")
        self.write("current_sprint.md", "# Sprint")

        result = cli.command_start(
            mode="product",
            root=self.root,
            emit="list",
            output=None,
            clipboard=False,
            agent=True,
        )
        self.assertEqual(result.exit_code, 0)
        messages = "\n".join(result.get("messages", []))
        self.assertIn("AGENT CONTEXT", messages)
        self.assertIn("Mode: product", messages)


if __name__ == "__main__":
    unittest.main()
