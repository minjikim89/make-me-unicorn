"""Injection rules: SQL built by string interpolation, unsafe deserialization, request data run as code."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from mmu_cli.vibecheck.analysis import JS_SUFFIXES, code, framework_of, is_test_file, low
from mmu_cli.vibecheck.engine import Finding, Location, Rule, _read, _rel, dedupe_locations, loc_at, loc_line, register

register(Rule(
    id="sql-fstring",
    title="SQL built with string interpolation",
    severity="P0",
    summary="Interpolating values into a SQL string (f-string, template literal, concatenation) lets request data rewrite the query (SQL injection).",
    fix=(
        "Pass values as bound parameters instead of interpolating them: cursor.execute(\"SELECT * FROM users WHERE id = %s\", (user_id,)) "
        "or SQLAlchemy text(\"... WHERE id = :id\") with {\"id\": user_id}.\n"
        "Table and column names cannot be bound: choose them from a hardcoded allowlist."
    ),
    fix_variants=(
        ("js", (
            "Pass values as bound parameters instead of interpolating them: db.query(\"SELECT * FROM users WHERE email = $1\", [email]) "
            "(node-postgres), `?` placeholders with mysql2/better-sqlite3, or a tagged template (sql`... ${value}`, prisma.$queryRaw`...`).\n"
            "Table and column names cannot be bound: choose them from a hardcoded allowlist."
        )),
    ),
    ref="https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
    tags=("injection",),
    confidence="high",
))

register(Rule(
    id="unsafe-deserialization",
    title="Unsafe deserialization",
    severity="P0",
    summary="pickle and non-safe YAML loaders execute code embedded in the data, so loading untrusted input is remote code execution.",
    fix=(
        "Use yaml.safe_load / yaml.safe_load_all (or Loader=yaml.SafeLoader) instead of yaml.load / unsafe_load / full_load.\n"
        "Replace pickle.load(s) on anything that crosses a trust boundary (uploads, caches, queues, network) with JSON or another data-only format."
    ),
    ref="https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html",
    tags=("injection", "python"),
    confidence="high",
))

register(Rule(
    id="code-injection",
    title="Request data executed as code",
    severity="P0",
    summary="Passing a request value to eval, new Function or a shell runs whatever the caller sends (remote code execution).",
    fix=(
        "Remove the dynamic execution. Parse data with JSON.parse / json.loads, map allowed operations through an "
        "explicit lookup table, and run external programs with an argument array (execFile / subprocess.run([...]) without shell=True) "
        "whose arguments are validated against an allowlist."
    ),
    ref="https://cwe.mitre.org/data/definitions/94.html",
    tags=("injection",),
    confidence="high",
))

# --- sql-fstring -------------------------------------------------------------

# A string that starts like a SQL statement (not prose that merely contains "select").
_SQL_SHAPE = re.compile(
    r"^\s*\(?\s*(?:with\s+\w+\s+as\s*\(|select\s[\s\S]*?\sfrom\s+\S|insert\s+into\s+\S|update\s+\S+\s+set\s+\S|"
    r"delete\s+from\s+\S|(?:drop|alter|truncate)\s+table\s)",
    re.IGNORECASE,
)
# The same shape with upper-case keywords: conventional SQL style, which prose never has.
_SQL_SHAPE_UPPER = re.compile(
    r"^\s*\(?\s*(?:WITH\s+\w+\s+AS\s*\(|SELECT\s[\s\S]*?\sFROM\s+\S|INSERT\s+INTO\s+\S|UPDATE\s+\S+\s+SET\s+\S|DELETE\s+FROM\s+\S)"
)
_SQL_SINKS = {
    "execute", "executemany", "executescript", "exec_driver_sql", "text", "raw", "query", "fetch", "fetchrow",
    "fetchval", "fetch_all", "fetch_one", "fetch_val", "read_sql", "read_sql_query", "run_sql", "execute_sql",
    "sql", "mogrify", "prepare",
}
# An interpolation right after one of these is an identifier (table/column), which cannot be bound.
_IDENT_POSITION = re.compile(r"(?:\b(?:from|into|update|join|table|by|exists|index|on|schema|database|select|as)|\.)\s*[\"`\[]?$", re.IGNORECASE)
_CONSTANT_NAME = re.compile(r"^(?:[\w.]+\.)?[A-Z_][A-Z0-9_]*$")  # module constant: SELECT ... FROM {TABLE}
_SAFE_EXPR = re.compile(r"placeholder|\bint\(|\bfloat\(|__tablename__|\.join\(|table|column|schema|fields?\b|cols?\b", re.IGNORECASE)


def _value_interpolations(parts: list[tuple[str, str | None]]) -> bool:
    """`parts` = (literal text before, interpolated expression source). True when a *value* is interpolated."""
    seen = ""
    for literal, expr in parts:
        seen += literal
        if expr is None:
            continue
        risky = not _IDENT_POSITION.search(seen) and not _SAFE_EXPR.search(expr) and not _CONSTANT_NAME.match(expr)
        seen += "x"
        if risky:
            return True
    return False


class _SqlVisitor(ast.NodeVisitor):
    """f-strings, %-formatting, .format() and concatenation that build SQL and reach an execute-like call."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.hits: list[int] = []
        self.sink_names: set[str] = set()
        self.assigned: dict[str, int] = {}

    def _parts(self, node: ast.AST) -> list[tuple[str, str | None]] | None:
        """(literal, interpolation) pieces of a string-building expression, or None when it is not one."""
        if isinstance(node, ast.JoinedStr):
            out: list[tuple[str, str | None]] = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    out.append((value.value, None))
                elif isinstance(value, ast.FormattedValue):
                    out.append(("", ast.get_source_segment(self.source, value.value) or "x"))
            return out
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                pieces = re.split(r"%(?:\(\w+\))?[sdr]", node.left.value)
                if len(pieces) > 1:
                    return [(piece, "x") for piece in pieces[:-1]] + [(pieces[-1], None)]
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self._parts(node.left)
            if left is None and isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                left = [(node.left.value, None)]
            if left is None:
                return None
            if isinstance(node.right, ast.Constant) and isinstance(node.right.value, str):
                return [*left, (node.right.value, None)]
            return [*left, ("", ast.get_source_segment(self.source, node.right) or "x")]
        if (
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format"
            and isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str) and (node.args or node.keywords)
        ):
            pieces = re.split(r"\{[^{}]*\}", node.func.value.value)
            if len(pieces) > 1:
                return [(piece, "x") for piece in pieces[:-1]] + [(pieces[-1], None)]
        return None

    def _is_sql(self, node: ast.AST, shape: re.Pattern[str] = _SQL_SHAPE) -> bool:
        parts = self._parts(node)
        if not parts or not any(expr is not None for _, expr in parts):
            return False
        literal = "".join(text + ("x" if expr is not None else "") for text, expr in parts)
        return bool(shape.match(literal)) and _value_interpolations(parts)

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._is_sql(node.value):
            if self._is_sql(node.value, _SQL_SHAPE_UPPER):
                self.hits.append(node.value.lineno)  # unmistakably SQL: flag even when the execute call is elsewhere
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.assigned[target.id] = node.value.lineno
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is not None and self._is_sql(node.value, _SQL_SHAPE_UPPER):
            self.hits.append(node.value.lineno)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
        if name in _SQL_SINKS:
            for arg in [*node.args[:2], *[kw.value for kw in node.keywords]]:
                if self._is_sql(arg):
                    self.hits.append(arg.lineno)
                elif isinstance(arg, ast.Name):
                    self.sink_names.add(arg.id)
        self.generic_visit(node)


def _python_sql_hits(text: str) -> list[int]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return []
    visitor = _SqlVisitor(text)
    visitor.visit(tree)
    hits = set(visitor.hits)
    hits.update(line for name, line in visitor.assigned.items() if name in visitor.sink_names)
    return sorted(hits)


_JS_SINK = r"\.(?:query|execute|raw|\$queryRawUnsafe|\$executeRawUnsafe|unsafe|prepare|exec|all|get|run|queryRaw|executeRaw)"
_JS_TEMPLATE_SQL = re.compile(_JS_SINK + r"\(\s*`((?:[^`\\]|\\.)*)`")
_JS_CONCAT_SQL = re.compile(_JS_SINK + r"""\(\s*(["'])((?:(?!\1)[^\\\n]|\\.)*)\1\s*\+\s*([^,)\n]+)""")
_JS_INTERP = re.compile(r"\$\{([^}]*)\}")


def _js_sql_hits(text: str) -> list[int]:
    """Offsets of query calls whose SQL is a template literal or concatenation with an interpolated value."""
    hits: list[int] = []
    if "`" in text:
        for m in _JS_TEMPLATE_SQL.finditer(text):
            body = m.group(1)
            if "${" not in body or not _SQL_SHAPE.match(_JS_INTERP.sub("x", body)):
                continue
            parts: list[tuple[str, str | None]] = []
            last = 0
            for interp in _JS_INTERP.finditer(body):
                parts.append((body[last:interp.start()], interp.group(1).strip() or "x"))
                last = interp.end()
            parts.append((body[last:], None))
            if _value_interpolations(parts):
                hits.append(m.start())
    for m in _JS_CONCAT_SQL.finditer(text):
        literal, expr = m.group(2), m.group(3).strip()
        if _SQL_SHAPE.match(literal) and _value_interpolations([(literal, expr), ("", None)]):
            hits.append(m.start())
    return sorted(hits)


def check_sql_strings(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    offenders: list[str] = []
    locations: list[Location] = []
    for path in code_files:
        suffix = path.suffix.lower()
        if suffix == ".py":
            text = _read(path)
            if not re.search(r"select|insert|update|delete", text, re.IGNORECASE):
                continue
            hits = [loc_line(path, root, lineno, text) for lineno in _python_sql_hits(text)]
        elif suffix in JS_SUFFIXES:
            text = code(path)
            hits = [loc_at(path, root, text, pos) for pos in _js_sql_hits(text)]
        else:
            continue
        if hits:
            offenders.append(_rel(path, root))
            locations.extend(hits)
    if offenders:
        first = root / locations[0].path
        return Finding(
            "sql-fstring",
            "P0",
            "fail",
            f"SQL built by interpolating values in {len(offenders)} file(s)",
            files=offenders,
            locations=dedupe_locations(locations),
            framework="js" if first.suffix.lower() in JS_SUFFIXES else "",
        )
    return Finding("sql-fstring", "P0", "ok", "no interpolated SQL reaching a query call")


# --- unsafe-deserialization --------------------------------------------------

_SAFE_YAML_LOADERS = {"SafeLoader", "CSafeLoader", "BaseLoader", "CBaseLoader"}
# The argument visibly crosses a trust boundary: request bodies, uploads, sockets, caches, decoded blobs.
_UNTRUSTED_ARG = re.compile(
    r"\brequest\b|\breq\b|upload|\.read\(\)|\bbody\b|payload|\.recv\(|b64decode|\.content\b|\.data\b|cookie|"
    r"\.form\b|\.files\b|\.json\b|redis|cache|\.get_data\(|message|socket|urlopen|\.text\b",
    re.IGNORECASE,
)


def _is_safe_yaml_loader(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id in _SAFE_YAML_LOADERS
    if isinstance(node, ast.Attribute):
        return node.attr in _SAFE_YAML_LOADERS
    return False


class _UnsafeDeserializationVisitor(ast.NodeVisitor):
    def __init__(self, source: str = "") -> None:
        self.source = source
        self.pickle_modules = {"pickle"}
        self.pickle_loaders: dict[str, str] = {}
        self.yaml_modules = {"yaml"}
        self.yaml_loaders: dict[str, str] = {}
        self.details: set[str] = set()
        self.hits: list[tuple[int, str]] = []
        self.untrusted: set[int] = set()  # lines whose argument visibly comes from outside the process

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            imported_as = alias.asname or alias.name
            if alias.name in {"pickle", "cPickle", "dill", "cloudpickle"}:
                self.pickle_modules.add(imported_as)
            elif alias.name == "yaml":
                self.yaml_modules.add(imported_as)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "pickle":
            for alias in node.names:
                if alias.name in {"load", "loads"}:
                    self.pickle_loaders[alias.asname or alias.name] = alias.name
        elif node.module == "yaml":
            for alias in node.names:
                if alias.name in {"load", "load_all", "unsafe_load", "unsafe_load_all", "full_load", "full_load_all"}:
                    self.yaml_loaders[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        label = self._pickle_label(node) if self._is_pickle_loader_call(node) else self._unsafe_yaml_loader_label(node)
        if label:
            self.details.add(label)
            self.hits.append((node.lineno, label))
            # YAML: the safe loader is always the right call. pickle: loading files the app wrote itself is legitimate.
            if label.startswith("yaml.") or (
                node.args and _UNTRUSTED_ARG.search(ast.get_source_segment(self.source, node.args[0]) or "")
            ):
                self.untrusted.add(node.lineno)
        self.generic_visit(node)

    def _is_pickle_loader_call(self, node: ast.Call) -> bool:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"load", "loads"}:
            return isinstance(func.value, ast.Name) and func.value.id in self.pickle_modules
        return isinstance(func, ast.Name) and func.id in self.pickle_loaders

    def _pickle_label(self, node: ast.Call) -> str:
        func = node.func
        if isinstance(func, ast.Attribute):
            return f"pickle.{func.attr}"
        if isinstance(func, ast.Name):
            return f"pickle.{self.pickle_loaders[func.id]}"
        return "pickle.load"

    def _unsafe_yaml_loader_label(self, node: ast.Call) -> str | None:
        func = node.func
        loader_name = None
        if isinstance(func, ast.Attribute) and func.attr in {
            "load",
            "load_all",
            "unsafe_load",
            "unsafe_load_all",
            "full_load",
            "full_load_all",
        }:
            if isinstance(func.value, ast.Name) and func.value.id in self.yaml_modules:
                loader_name = func.attr
        elif isinstance(func, ast.Name):
            loader_name = self.yaml_loaders.get(func.id)
        if loader_name is None:
            return None
        if loader_name not in {"load", "load_all"}:
            return f"yaml.{loader_name}"
        if any(keyword.arg == "Loader" and _is_safe_yaml_loader(keyword.value) for keyword in node.keywords):
            return None
        if len(node.args) >= 2 and _is_safe_yaml_loader(node.args[1]):  # yaml.load(stream, yaml.SafeLoader)
            return None
        return f"yaml.{loader_name} without SafeLoader"


def _deserialization_scan(text: str) -> tuple[list[tuple[int, str]], set[int]]:
    """((line, label) for every unsafe pickle/yaml call, lines whose input is visibly untrusted)."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return [], set()
    visitor = _UnsafeDeserializationVisitor(text)
    visitor.visit(tree)
    return sorted(visitor.hits), visitor.untrusted


def _unsafe_deserialization_hits(text: str) -> list[tuple[int, str]]:
    """(line, label) for every unsafe pickle/yaml call in a Python source text."""
    return _deserialization_scan(text)[0]


def _unsafe_deserialization_details(text: str) -> set[str]:
    return {label for _, label in _unsafe_deserialization_hits(text)}


def deserialization_findings(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> list[Finding]:
    """P0 for unsafe YAML loaders and for pickle on data that visibly comes from outside the process; P1 for other pickle loads."""
    tiers: dict[str, tuple[list[Location], set[str]]] = {"P0": ([], set()), "P1": ([], set())}
    for path in code_files:
        if path.suffix.lower() != ".py":
            continue
        text = _read(path)
        if "pickle" not in text and "yaml" not in text and "dill" not in text:
            continue
        hits, untrusted = _deserialization_scan(text)
        for lineno in dict.fromkeys(n for n, _ in hits):
            labels = {label for n, label in hits if n == lineno}
            locations, details = tiers["P0" if lineno in untrusted else "P1"]
            locations.append(loc_line(path, root, lineno, text))
            details.update(labels)
    out: list[Finding] = []
    blocking, details = tiers["P0"]
    if blocking:
        files = sorted({loc.path for loc in blocking})
        out.append(Finding(
            "unsafe-deserialization",
            "P0",
            "fail",
            f"unsafe deserialization in {len(files)} file(s): " + ", ".join(sorted(details)),
            files=files,
            locations=blocking,
        ))
    warned, details = tiers["P1"]
    if warned:
        files = sorted({loc.path for loc in warned})
        out.append(Finding(
            "unsafe-deserialization",
            "P1",
            "warn",
            f"pickle load in {len(files)} file(s) whose input source is not visible (safe only for files the app wrote itself): "
            + ", ".join(sorted(details)),
            files=files,
            locations=warned,
            confidence="medium",
        ))
    if not out:
        out.append(Finding("unsafe-deserialization", "P0", "ok", "no unsafe Python deserialization detected"))
    return out


def check_unsafe_deserialization(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    """The most severe unsafe-deserialization finding (`deserialization_findings` returns both tiers)."""
    return deserialization_findings(root, code_files, config_files)[0]


# --- code-injection ----------------------------------------------------------

_JS_REQUEST = (
    r"\b(?:req|request|ctx\.request|ctx|event)\.(?:body|query|params|headers|cookies)\b|\bc\.req\.(?:query|param|json|header|text)\(|"
    r"searchParams\.get\(|\bformData\.get\("
)
_PY_REQUEST = (
    r"\brequest\.(?:args|form|json|data|values|query_params|GET|POST|body|cookies|headers|files|path_params)\b|"
    r"\.get_json\(\)|\bawait\s+request\.(?:json|body|form)\(\)"
)
_JS_EXEC = re.compile(
    r"(?<![.\w$])eval\(|\bnew\s+Function\(|(?<![.\w$])(?:exec|execSync|spawn|spawnSync)\(|\bchild_process\.(?:exec|execSync|spawn|spawnSync)\(|"
    r"\bcp\.(?:exec|execSync)\(|\bvm\.(?:runInNewContext|runInThisContext|runInContext)\(|\bnew\s+vm\.Script\("
)
_PY_EXEC = re.compile(
    r"(?<![.\w])(?:eval|exec)\(|\bos\.(?:system|popen)\(|\bsubprocess\.(?:run|call|check_output|check_call|Popen|getoutput)\("
)
_JS_REQUEST_RE = re.compile(_JS_REQUEST)
_PY_REQUEST_RE = re.compile(_PY_REQUEST)
_EXEC_HINTS = ("eval(", "function(", "exec", "spawn", "vm.", "os.system", "os.popen", "subprocess")
_BARE_EXEC = re.compile(r"(?<![.\w$])(?:exec|execSync|spawn|spawnSync)\($")


def _call_args(text: str, open_paren: int, limit: int = 400) -> str:
    """Source of a call's argument list, from the opening parenthesis to its match (bounded)."""
    depth = 0
    end = min(len(text), open_paren + limit)
    for i in range(open_paren, end):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[open_paren + 1: i]
    return text[open_paren + 1: end]


def check_code_injection(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    """eval / new Function / shell execution whose argument visibly comes from the request, in the same expression."""
    locations: list[Location] = []
    for path in code_files:
        suffix = path.suffix.lower()
        if suffix in JS_SUFFIXES:
            execs, request = _JS_EXEC, _JS_REQUEST_RE
        elif suffix == ".py":
            execs, request = _PY_EXEC, _PY_REQUEST_RE
        else:
            continue
        if is_test_file(path, root):
            continue
        lowered = low(path)
        if not any(hint in lowered for hint in _EXEC_HINTS) or "req" not in lowered and "searchparams" not in lowered and "formdata" not in lowered:
            continue
        text = code(path)
        for m in execs.finditer(text):
            if suffix != ".py" and _BARE_EXEC.search(m.group(0)) and "child_process" not in text:
                continue  # exec()/spawn() that is not node's child_process
            args = _call_args(text, m.end() - 1)
            if not request.search(args):
                continue
            if suffix == ".py" and m.group(0).startswith("subprocess.") and not re.search(r"shell\s*=\s*True", args):
                continue  # argument-array form: no shell, no injection through the command string
            locations.append(loc_at(path, root, text, m.start()))
    if locations:
        files = sorted({loc.path for loc in locations})
        return Finding(
            "code-injection",
            "P0",
            "fail",
            f"request data passed to eval/exec/shell in {len(files)} file(s)",
            files=files,
            locations=dedupe_locations(locations),
            framework=framework_of(root / locations[0].path, root),
        )
    return Finding("code-injection", "P0", "ok", "no request data reaching eval, new Function or a shell")
