"""MCP server exposing MMU blueprints and idea templates as agent tools.

Imports `mcp` lazily so the package stays installable without the optional
extra. Install with `pip install make-me-unicorn[mcp]`.
"""

from __future__ import annotations

from pathlib import Path


def _resolve_repo_root(root: Path | None) -> Path:
    if root is not None:
        if (root / "docs" / "blueprints").is_dir():
            return root
        raise FileNotFoundError(
            f"--root {root} does not contain docs/blueprints/. "
            "Point it at a checkout of make-me-unicorn, or omit --root to use the package install location."
        )
    pkg_root = Path(__file__).resolve().parents[2]
    if (pkg_root / "docs" / "blueprints").is_dir():
        return pkg_root
    raise FileNotFoundError(
        "Could not locate docs/blueprints/. Pass --root <path-to-make-me-unicorn>."
    )


def _list_blueprint_files(repo: Path) -> list[Path]:
    core = sorted((repo / "docs" / "blueprints").glob("*.md"))
    industry_dir = repo / "docs" / "blueprints" / "industry"
    industry = sorted(industry_dir.glob("*.md")) if industry_dir.is_dir() else []
    return [p for p in core if p.name != "README.md"] + [p for p in industry if p.name != "README.md"]


def _list_idea_template_files(repo: Path) -> list[Path]:
    files: list[Path] = []
    prompts_dir = repo / "prompts"
    if prompts_dir.is_dir():
        files.extend(sorted(prompts_dir.glob("*.md")))
    launch_dir = repo / "docs" / "launch"
    if launch_dir.is_dir():
        files.extend(sorted(launch_dir.glob("*.md")))
    return files


def _summarize(path: Path, repo: Path) -> dict[str, str]:
    rel = path.relative_to(repo).as_posix()
    name = path.stem
    description = ""
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    description = stripped.lstrip("# ").strip()
                    break
    except OSError:
        pass
    return {"name": name, "path": rel, "description": description}


def list_blueprints(root: Path | None = None) -> list[dict[str, str]]:
    repo = _resolve_repo_root(root)
    return [_summarize(p, repo) for p in _list_blueprint_files(repo)]


def get_blueprint(name: str, root: Path | None = None) -> dict[str, str]:
    repo = _resolve_repo_root(root)
    for path in _list_blueprint_files(repo):
        if path.stem == name or path.stem.split("-", 1)[-1] == name:
            return {
                "name": path.stem,
                "path": path.relative_to(repo).as_posix(),
                "content": path.read_text(encoding="utf-8"),
            }
    raise ValueError(f"Blueprint not found: {name}")


def list_idea_templates(root: Path | None = None) -> list[dict[str, str]]:
    repo = _resolve_repo_root(root)
    return [_summarize(p, repo) for p in _list_idea_template_files(repo)]


def validate_idea(idea: str) -> dict[str, str]:
    return {
        "status": "stub",
        "idea": idea,
        "note": (
            "Full idea validation is intentionally not exposed over MCP yet — it requires "
            "external HTTP scraping (HN + Reddit) and optional LLM synthesis, which take "
            "several seconds and don't fit a stdio tool round-trip. "
            "Run `mmu validate \"<idea>\"` in your terminal for the free local mode, "
            "or `mmu validate \"<idea>\" --llm` for an Anthropic-synthesized verdict."
        ),
    }


def build_server(root: Path | None = None):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise ImportError(
            "MCP server requires the optional extra. Install with "
            "`pip install make-me-unicorn[mcp]`."
        ) from exc

    # Fail fast at startup if root is unusable, instead of letting every
    # tool call surface the same error after the client is already wired up.
    _resolve_repo_root(root)

    mcp = FastMCP("make-me-unicorn")

    @mcp.tool()
    def mmu_list_blueprints() -> list[dict[str, str]]:
        """List all available MMU blueprints (core + industry) with name, path, and one-line description."""
        return list_blueprints(root)

    @mcp.tool()
    def mmu_get_blueprint(name: str) -> dict[str, str]:
        """Fetch the full markdown content of a single blueprint by name (e.g. 'frontend', 'billing', 'ai-product')."""
        return get_blueprint(name, root)

    @mcp.tool()
    def mmu_list_idea_templates() -> list[dict[str, str]]:
        """List MMU idea + launch templates (start/close/ADR prompts, Product Hunt kit)."""
        return list_idea_templates(root)

    @mcp.tool()
    def mmu_validate_idea(idea: str) -> dict[str, str]:
        """Validate a startup idea. v0.6 stub — full validation lives in `mmu validate <idea>`."""
        return validate_idea(idea)

    return mcp


def serve(root: Path | None = None, transport: str = "stdio") -> None:
    server = build_server(root)
    server.run(transport=transport)
