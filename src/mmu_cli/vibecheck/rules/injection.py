"""Injection rules: f-string SQL and unsafe Python deserialization."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from mmu_cli.vibecheck.engine import Finding, _read, _rel

_SQL_FSTRING = re.compile(r"""f["']\s*(?:SELECT|INSERT|UPDATE|DELETE)\b""", re.IGNORECASE)


def check_sql_strings(root: Path, code_files: list[Path]) -> Finding:
    offenders = []
    for path in code_files:
        if path.suffix.lower() != ".py":
            continue
        if _SQL_FSTRING.search(_read(path)):
            offenders.append(_rel(path, root))
    if offenders:
        return Finding(
            "sql-fstring",
            "P0",
            "fail",
            f"f-string SQL queries in {len(offenders)} file(s)",
            hint="Interpolating values into SQL is the classic AI-generated injection hole. Use parameterized queries.",
            files=offenders,
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
        if self._is_pickle_loader_call(node):
            self.details.add(self._pickle_label(node))
        else:
            yaml_label = self._unsafe_yaml_loader_label(node)
            if yaml_label:
                self.details.add(yaml_label)
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


def _unsafe_deserialization_details(text: str) -> set[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    visitor = _UnsafeDeserializationVisitor()
    visitor.visit(tree)
    return visitor.details


def check_unsafe_deserialization(root: Path, code_files: list[Path]) -> Finding:
    offenders: list[str] = []
    details: list[str] = []
    for path in code_files:
        if path.suffix.lower() != ".py":
            continue
        text = _read(path)
        file_details = _unsafe_deserialization_details(text)
        if file_details:
            offenders.append(_rel(path, root))
            details.extend(sorted(file_details))
    if offenders:
        return Finding(
            "unsafe-deserialization",
            "P0",
            "fail",
            f"unsafe deserialization in {len(offenders)} file(s): " + ", ".join(sorted(set(details))),
            hint="Do not deserialize untrusted input with pickle or unsafe YAML loaders. Prefer JSON or yaml.safe_load.",
            files=sorted(set(offenders)),
        )
    return Finding("unsafe-deserialization", "P0", "ok", "no unsafe Python deserialization detected")
