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
    from mmu_cli._data import find_content_root

    content_root = find_content_root()
    if content_root is not None:
        return content_root
    raise FileNotFoundError(
        "Could not locate docs/blueprints/ in the repo checkout or the packaged wheel data. "
        "Pass --root <path-to-make-me-unicorn>, or reinstall: pip install --force-reinstall make-me-unicorn"
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
    matches = []
    for path in _list_blueprint_files(repo):
        if path.stem == name or path.stem.split("-", 1)[-1] == name:
            matches.append(path)

    if len(matches) > 1:
        stems = [p.name for p in matches]
        raise ValueError(
            f"Multiple blueprints matched '{name}': {', '.join(stems)}. "
            "Please specify the exact name."
        )
    elif len(matches) == 1:
        path = matches[0]
        return {
            "name": path.stem,
            "path": path.relative_to(repo).as_posix(),
            "content": path.read_text(encoding="utf-8"),
        }
    raise ValueError(f"Blueprint not found: {name}")


def list_idea_templates(root: Path | None = None) -> list[dict[str, str]]:
    repo = _resolve_repo_root(root)
    return [_summarize(p, repo) for p in _list_idea_template_files(repo)]


def _missing_validate_extra() -> bool:
    """The validators package imports lazily; check the [validate] extra's real
    dependencies up front so a missing extra becomes one friendly payload
    instead of an ImportError leaking out of a tool call."""
    try:
        import requests  # type: ignore[import-untyped] # noqa: F401
        import vaderSentiment  # noqa: F401
    except ImportError:
        return True
    return False


def validate_idea(idea: str, limit: int = 20) -> dict:
    """Run the free validation pipeline (HN + Reddit search, local VADER sentiment).

    Mirrors `mmu validate <idea>` default mode: no API keys, no paid calls.
    LLM synthesis stays CLI-only (`mmu validate --llm`) because it is a paid,
    interactive opt-in.
    """
    if _missing_validate_extra():
        return {
            "status": "unavailable",
            "idea": idea,
            "note": (
                "Idea validation needs the [validate] extra. "
                "Install with `pip install make-me-unicorn[validate]` "
                "(or `[all]`), then call this tool again."
            ),
        }

    from mmu_cli.validators import analyze_sentiment, extract_competitors, fetch_threads
    from mmu_cli.validators.report import verdict

    hits, errors = fetch_threads(idea, limit=limit)
    if errors and not hits:
        return {"status": "error", "idea": idea, "errors": errors}

    texts = [(h.get("title") or "") + " " + (h.get("text") or "") for h in hits]
    sentiment = (
        analyze_sentiment(texts)
        if texts
        else {"compound": 0.0, "count": 0, "pos": 0.0, "neg": 0.0, "neu": 0.0}
    )
    competitors = extract_competitors(texts) if texts else []

    return {
        "status": "ok",
        "idea": idea,
        "threads_found": len(hits),
        "verdict": verdict(sentiment.get("compound", 0.0), int(sentiment.get("count", 0))),
        "sentiment": sentiment,
        "competitors": [{"name": n, "mentions": c} for n, c in competitors],
        "top_threads": [
            {
                "source": h.get("source", "?"),
                "title": h.get("title", ""),
                "url": h.get("url", ""),
            }
            for h in hits[:10]
        ],
        "errors": errors,
        "note": (
            "Free mode: public HN + Reddit search with local VADER sentiment. "
            'For a synthesized 1-page verdict, run `mmu validate "<idea>" --llm` in a terminal.'
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
    def mmu_vibecheck(project_root: str) -> dict:
        """Scan a codebase for the launch-blocking gaps AI-generated code ships most.

        Use when: the user is about to commit, deploy, or launch, or asks "is this
        safe to ship?" about a project on disk. Deterministic and read-only — no
        LLM, no network, runs in under a second on most repos.

        Args:
            project_root: absolute path of the project to scan (the git root).

        Returns: {"findings": [{check, severity (P0|P1), status (fail|warn|ok|skip),
        message, hint, files, ref}], "failures": <count of P0 fails>, "exit_code"}.
        P0 fails mean "do not ship yet"; `ref` links the incident data behind the rule.
        Do NOT use for: reviewing code style or architecture — this only checks the
        specific gaps listed in each finding.
        """
        from mmu_cli.cli import command_vibecheck

        result = command_vibecheck(Path(project_root))
        return {
            "findings": result.get("findings", []),
            "failures": result.get("failures", 0),
            "exit_code": result.exit_code,
        }

    @mcp.tool()
    def mmu_validate_idea(idea: str, limit: int = 20) -> dict:
        """Check a startup idea against real Hacker News + Reddit threads.

        Use when: the user describes a product idea and wants to know if people
        already complain about the problem, who the competitors are, and how the
        sentiment leans. Free mode — public search + local sentiment, no API keys.

        Args:
            idea: one sentence describing the product (e.g. "invoice reminders for freelancers").
            limit: max threads to fetch per source (default 20).

        Returns: {"verdict", "sentiment", "competitors": [...], "threads": [{title, url,
        source, score, created_at}]}. Treat `threads` as the evidence and `verdict`
        as a summary of it, not the other way round.
        """
        return validate_idea(idea, limit=limit)

    @mcp.tool()
    def mmu_get_blueprint(name: str) -> dict[str, str]:
        """Fetch one MMU launch blueprint (a checklist of what a shipped SaaS needs in one area).

        Use when: the user asks what they must have before launch for a specific
        area — billing, auth/security, frontend, backend, ai-product, marketplace…
        Call mmu_list_blueprints first if you do not know the exact name.

        Args:
            name: blueprint slug, e.g. "billing", "security", "ai-product".

        Returns: {"name", "path", "content"} where content is the full markdown
        checklist. Raises ValueError if the name is unknown or ambiguous.
        """
        return get_blueprint(name, root)

    @mcp.tool()
    def mmu_list_blueprints() -> list[dict[str, str]]:
        """List the available MMU launch blueprints (15 core + industry) with a one-line description each.

        Use when: you need the exact slug to pass to mmu_get_blueprint, or the user
        asks "what areas does a launch checklist cover?". Cheap; returns ~20 rows.

        Returns: [{"name", "path", "description"}].
        """
        return list_blueprints(root)

    @mcp.tool()
    def mmu_list_idea_templates() -> list[dict[str, str]]:
        """List MMU prompt templates: session start/close, ADR, and the Product Hunt launch kit.

        Use when: the user wants a structured prompt for planning a work session,
        recording a decision, or drafting a Product Hunt launch. Returns names and
        paths only; read the file for the template body.

        Returns: [{"name", "path"}].
        """
        return list_idea_templates(root)

    return mcp


def serve(root: Path | None = None, transport: str = "stdio") -> None:
    server = build_server(root)
    server.run(transport=transport)
