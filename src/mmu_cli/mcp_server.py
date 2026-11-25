"""MCP server: the vibecheck launch gate, rule lookup, blueprints, and idea validation as agent tools.

Imports `mcp` lazily so the package stays installable without the optional
extra. Install with `pip install make-me-unicorn[mcp]`.

Works with both majors of the MCP Python SDK: v2 (`mcp.server.MCPServer`) and
v1 (`mcp.server.fastmcp.FastMCP`, >= 1.27). `_load_sdk` hides the difference.
"""

import json
from pathlib import Path
from typing import Annotated, Any


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


INSTRUCTIONS = (
    "Make Me Unicorn is a deterministic launch gate for code written by AI agents (no LLM, no network, no account). "
    "Call `mmu_vibecheck` with the project's absolute path and scope=\"changed\" after you write or change webhook "
    "handlers, auth/login/password code, payment code, Supabase migrations or RLS, CORS or rate limits, env vars or "
    "API keys, and always before you commit, open a PR, deploy, or tell the user the work is done. "
    "`summary.blocking` > 0 means not done: fix each P0 finding at its `locations` using its `fix`, then call the "
    "tool again until blocking is 0. Use `mmu_explain_rule` when a finding is unclear. Do not silence a finding to "
    "pass the gate; a real false positive takes a `mmu-ignore[<rule-id>]: <reason>` comment on the flagged line. "
    "The blueprint and idea-validation tools are for planning, not for gating."
)


def package_version() -> str:
    try:
        from importlib.metadata import version

        return version("make-me-unicorn")
    except Exception:
        return "0+unknown"


def _load_sdk() -> tuple[Any, int, type[Exception]]:
    """Return (server class, SDK major, ToolError). v2 renamed FastMCP to MCPServer and removed `mcp.server.fastmcp`."""
    try:
        from mcp.server import MCPServer  # type: ignore[attr-defined]
        from mcp.server.mcpserver.exceptions import ToolError as ToolErrorV2  # type: ignore[import-not-found]

        return MCPServer, 2, ToolErrorV2
    except ImportError:
        pass
    try:
        from mcp.server.fastmcp import FastMCP
        from mcp.server.fastmcp.exceptions import ToolError

        return FastMCP, 1, ToolError
    except ImportError as exc:
        raise ImportError(
            "MCP server requires the optional extra. Install with "
            "`pip install make-me-unicorn[mcp]`."
        ) from exc


def sdk_major() -> int | None:
    """Major version of the installed MCP SDK, or None when it is not installed."""
    try:
        return _load_sdk()[1]
    except ImportError:
        return None


def _output_models() -> Any:
    """Pydantic models for the `mmu.vibecheck/v1` document; they become the tool's output schema.

    Built lazily because pydantic arrives with the `mcp` extra. Unknown keys are allowed: v1 only
    ever adds fields, and a newer scanner must not fail validation in an older server.
    """
    from pydantic import BaseModel, ConfigDict, Field

    class _Open(BaseModel):
        model_config = ConfigDict(extra="allow", populate_by_name=True)

    class Location(_Open):
        path: str
        line: int | None = None
        end_line: int | None = None
        snippet: str | None = None

    class Finding(_Open):
        rule_id: str
        severity: str = Field(description="P0 blocks, P1 warns")
        status: str = Field(description="fail (blocking), warn, suppressed, ok, skip")
        title: str = ""
        message: str = ""
        locations: list[Location] = Field(default_factory=list)
        files: list[str] = Field(default_factory=list)
        fix: str = Field(default="", description="Concrete instructions for fixing this finding")
        ref: str = ""
        confidence: str = ""
        suppression: dict[str, Any] | None = None
        notes: list[str] = Field(default_factory=list)
        fingerprint: str = ""

    class Summary(_Open):
        blocking: int = Field(description="P0 findings; > 0 means do not ship yet")
        warnings: int = 0
        passed: int = 0
        skipped: int = 0
        suppressed: int = 0

    class VibecheckDocument(_Open):
        schema_id: str = Field(alias="schema", description="Always mmu.vibecheck/v1")
        tool: dict[str, Any]
        root: str
        scope: dict[str, Any]
        summary: Summary
        findings: list[Finding]

    return VibecheckDocument


def vibecheck_tool(project_root: str, scope: str = "all", format: str = "json") -> tuple[dict[str, Any], str]:
    """Run the scan for the MCP tool. Returns (v1 document, text for the model in `format`)."""
    from mmu_cli.vibecheck.engine import ScanError, scan
    from mmu_cli.vibecheck.output import render_agent, to_json

    target = Path(project_root).expanduser()
    if not target.is_dir():
        raise ValueError(f"project_root is not a directory: {project_root}")
    if scope not in {"all", "changed", "staged"}:
        raise ValueError(f"scope must be all, changed, or staged (got {scope!r})")
    if format not in {"json", "agent"}:
        raise ValueError(f"format must be json or agent (got {format!r})")
    try:
        result = scan(target, scope=scope)
    except ScanError as exc:
        raise ValueError(f"{exc.code}: {exc.message}") from None
    document = to_json(result)
    text = render_agent(result) if format == "agent" else json.dumps(document, ensure_ascii=False)
    return document, text


def explain_rule(rule_id: str) -> dict[str, Any]:
    from mmu_cli.vibecheck.engine import ScanError, all_rules, get_rule

    try:
        return get_rule(rule_id).to_dict()
    except ScanError:
        known = ", ".join(rule.id for rule in all_rules())
        raise ValueError(f"unknown rule id {rule_id!r}. Known rules: {known}") from None


def list_rules() -> list[dict[str, Any]]:
    from mmu_cli.vibecheck.engine import all_rules

    return [
        {"id": r.id, "title": r.title, "severity": r.severity, "summary": r.summary, "tags": list(r.tags)}
        for r in all_rules()
    ]


def build_server(root: Path | None = None) -> Any:
    server_cls, major, tool_error = _load_sdk()
    from mcp.types import CallToolResult, TextContent, ToolAnnotations

    def user_error(fn: Any, *args: Any, **kwargs: Any) -> Any:
        # SDK v2 hides the text of unexpected exceptions from the model; a ToolError is passed through.
        try:
            return fn(*args, **kwargs)
        except ValueError as exc:
            raise tool_error(str(exc)) from None

    # Fail fast at startup if root is unusable, instead of letting every
    # tool call surface the same error after the client is already wired up.
    _resolve_repo_root(root)

    version = package_version()
    if major >= 2:
        mcp = server_cls("make-me-unicorn", instructions=INSTRUCTIONS, version=version)
    else:
        mcp = server_cls("make-me-unicorn", instructions=INSTRUCTIONS)
        # FastMCP (v1) has no version argument; without this serverInfo reports the SDK's version.
        lowlevel = getattr(mcp, "_mcp_server", None)
        if lowlevel is not None:
            lowlevel.version = version

    # camelCase works in both majors (v2 keeps it as the wire alias).
    local_read_only = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)
    web_read_only = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
    document_model = _output_models()

    def mmu_vibecheck(project_root: str, scope: str = "all", format: str = "json"):  # type: ignore[no-untyped-def]
        """Scan a codebase for the launch-blocking gaps AI-generated code ships most.

        Use when: you just wrote or changed webhook, auth, payment, Supabase/RLS, CORS,
        rate-limit, env-var or SQL code; you are about to commit, open a PR, deploy, or
        declare a task done; or the user asks "is this safe to ship?". Deterministic and
        read-only: no LLM, no network, under a second on most repos.

        Args:
            project_root: absolute path of the project to scan (the git root).
            scope: "all" (default, whole project), "changed" (files changed vs HEAD
                plus untracked), or "staged" (staged files). Scoped scans need git.
            format: "json" (default) returns the document as text; "agent" returns compact
                text (rule id, path:line, fix, how to silence). Structured content is the
                same `mmu.vibecheck/v1` document either way.

        Returns the `mmu.vibecheck/v1` document: {"schema", "tool", "root", "scope",
        "summary": {blocking, warnings, passed, skipped, suppressed}, "findings":
        [{rule_id, severity (P0|P1), status (fail|warn|suppressed), title, message,
        locations: [{path, line, end_line, snippet}], files, fix, ref, confidence,
        suppression, notes}]}. `summary.blocking` > 0 means "do not ship yet": apply
        each finding's `fix` at its `locations`, then scan again. A false positive is
        silenced with a `mmu-ignore[<rule_id>]: <reason>` comment on the flagged line.
        Do NOT use for: reviewing code style or architecture. This only checks the
        specific gaps listed in each finding.
        """
        document, text = user_error(vibecheck_tool, project_root, scope, format)
        return CallToolResult(content=[TextContent(type="text", text=text)], structuredContent=document)

    # `Annotated[CallToolResult, Model]`: the tool controls its text content and the SDK
    # publishes Model as the output schema and validates the structured content against it.
    mmu_vibecheck.__annotations__["return"] = Annotated[CallToolResult, document_model]
    mcp.tool(title="Vibecheck launch gate", annotations=local_read_only)(mmu_vibecheck)

    @mcp.tool(title="Explain a vibecheck rule", annotations=local_read_only)
    def mmu_explain_rule(rule_id: str) -> dict[str, Any]:
        """Explain one vibecheck rule: what it detects, why it matters, and the fix.

        Use when: a `mmu_vibecheck` finding is unclear, you need the full fix
        instructions, or you must decide whether a finding is a false positive.

        Args:
            rule_id: the finding's `rule_id`, e.g. "webhook-signature", "supabase-rls".

        Returns: {"id", "title", "severity", "summary", "fix", "ref", "tags", "confidence"}.
        Raises ValueError listing the known ids when the id is unknown.
        """
        return user_error(explain_rule, rule_id)

    @mcp.tool(title="List vibecheck rules", annotations=local_read_only)
    def mmu_list_rules() -> list[dict[str, Any]]:
        """List every vibecheck rule with its id, severity and one-line summary.

        Use when: the user asks what the launch gate checks, or you need a rule id
        for `mmu_explain_rule` or for a `mmu-ignore[<rule-id>]: <reason>` marker.

        Returns: [{"id", "title", "severity" (P0 blocks, P1 warns), "summary", "tags"}].
        """
        return list_rules()

    @mcp.tool(title="Validate a startup idea", annotations=web_read_only)
    def mmu_validate_idea(idea: str, limit: int = 20) -> dict[str, Any]:
        """Check a startup idea against real Hacker News + Reddit threads.

        Use when: the user describes a product idea and wants to know if people
        already complain about the problem, who the competitors are, and how the
        sentiment leans. Free mode: public search + local sentiment, no API keys.
        Calls the public HN and Reddit search APIs.

        Args:
            idea: one sentence describing the product (e.g. "invoice reminders for freelancers").
            limit: max threads to fetch per source (default 20).

        Returns: {"status": "ok", "verdict", "sentiment", "threads_found",
        "competitors": [{name, mentions}], "top_threads": [{source, title, url}],
        "errors", "note"}. Treat `top_threads` as the evidence and `verdict` as a
        summary of it. When the `[validate]` extra is missing the result is
        {"status": "unavailable", "note"}; on search failure {"status": "error", "errors"}.
        Neither carries a verdict, so check `status` first.
        """
        return validate_idea(idea, limit=limit)

    @mcp.tool(title="Get a launch blueprint", annotations=local_read_only)
    def mmu_get_blueprint(name: str) -> dict[str, str]:
        """Fetch one MMU launch blueprint (a checklist of what a shipped SaaS needs in one area).

        Use when: the user asks what they must have before launch for a specific
        area: billing, auth/security, frontend, backend, ai-product, marketplace…
        Call mmu_list_blueprints first if you do not know the exact name.

        Args:
            name: blueprint slug, e.g. "billing", "security", "ai-product".

        Returns: {"name", "path", "content"} where content is the full markdown
        checklist. Raises ValueError if the name is unknown or ambiguous.
        """
        return user_error(get_blueprint, name, root)

    @mcp.tool(title="List launch blueprints", annotations=local_read_only)
    def mmu_list_blueprints() -> list[dict[str, str]]:
        """List the available MMU launch blueprints (15 core + 2 industry) with a one-line description each.

        Use when: you need the exact slug to pass to mmu_get_blueprint, or the user
        asks "what areas does a launch checklist cover?". Cheap; returns 17 rows.

        Returns: [{"name", "path", "description"}].
        """
        return list_blueprints(root)

    @mcp.tool(title="List prompt templates", annotations=local_read_only)
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
