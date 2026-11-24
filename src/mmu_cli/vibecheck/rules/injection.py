"""Injection rules: f-string SQL and unsafe Python deserialization."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from mmu_cli.vibecheck.engine import Finding, Location, Rule, _read, _rel, loc_at, loc_line, register

register(Rule(
    id="sql-fstring",
    title="SQL built with an f-string",
    severity="P0",
    summary="Interpolating values into a SQL string lets request data rewrite the query (SQL injection).",
    fix=(
        "Pass values as bound parameters instead of interpolating them: cursor.execute(\"SELECT * FROM users WHERE id = %s\", (user_id,)) "
        "or SQLAlchemy text(\"... WHERE id = :id\") with {\"id\": user_id}.\n"
        "Table and column names cannot be bound: choose them from a hardcoded allowlist."
    ),
    ref="https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
    tags=("injection", "python"),
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

_SQL_FSTRING = re.compile(r"""f["']\s*(?:SELECT|INSERT|UPDATE|DELETE)\b""", re.IGNORECASE)


def check_sql_strings(root: Path, code_files: list[Path]) -> Finding:
    offenders = []
    locations: list[Location] = []
    for path in code_files:
        if path.suffix.lower() != ".py":
            continue
        text = _read(path)
        hits = [loc_at(path, root, text, m.start()) for m in _SQL_FSTRING.finditer(text)]
        if hits:
            offenders.append(_rel(path, root))
            locations.extend(hits)
    if offenders:
        return Finding(
            "sql-fstring",
            "P0",
            "fail",
            f"f-string SQL queries in {len(offenders)} file(s)",
            files=offenders,
            locations=locations,
        )
    return Finding("sql-fstring", "P0", "ok", "no f-string SQL queries detected")


def _is_safe_yaml_loader(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id in {"SafeLoader", "CSafeLoader"}
    if isinstance(node, ast.Attribute):
        return node.attr in {"SafeLoader", "CSafeLoader"}
    return False


class _UnsafeDeserializationVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.pickle_modules = {"pickle"}
        self.pickle_loaders: dict[str, str] = {}
        self.yaml_modules = {"yaml"}
        self.yaml_loaders: dict[str, str] = {}
        self.details: set[str] = set()
        self.hits: list[tuple[int, str]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            imported_as = alias.asname or alias.name
            if alias.name == "pickle":
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
        return f"yaml.{loader_name} without SafeLoader"


def _unsafe_deserialization_hits(text: str) -> list[tuple[int, str]]:
    """(line, label) for every unsafe pickle/yaml call in a Python source text."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    visitor = _UnsafeDeserializationVisitor()
    visitor.visit(tree)
    return sorted(visitor.hits)


def _unsafe_deserialization_details(text: str) -> set[str]:
    return {label for _, label in _unsafe_deserialization_hits(text)}


def check_unsafe_deserialization(root: Path, code_files: list[Path]) -> Finding:
    offenders: list[str] = []
    details: list[str] = []
    locations: list[Location] = []
    for path in code_files:
        if path.suffix.lower() != ".py":
            continue
        text = _read(path)
        hits = _unsafe_deserialization_hits(text)
        if hits:
            offenders.append(_rel(path, root))
            details.extend(sorted({label for _, label in hits}))
            locations.extend(loc_line(path, root, lineno, text) for lineno in dict.fromkeys(n for n, _ in hits))
    if offenders:
        return Finding(
            "unsafe-deserialization",
            "P0",
            "fail",
            f"unsafe deserialization in {len(offenders)} file(s): " + ", ".join(sorted(set(details))),
            files=sorted(set(offenders)),
            locations=locations,
        )
    return Finding("unsafe-deserialization", "P0", "ok", "no unsafe Python deserialization detected")
