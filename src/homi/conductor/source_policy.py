"""Canonical source policy for primitive-only PixCell programs.

This module is deliberately dependency-free so the conductor and training
evaluator apply the same AST-based policy before any candidate is executed.
The frozen dataset capsule records the policy used when its rows were admitted.
Release validation also applies this current canonical policy, which may add
safe restrictions without changing the frozen release.
"""

from __future__ import annotations

import ast
import re


ALLOWED_COMPONENTS = frozenset(
    {
        "L",
        "bend_circular",
        "bend_euler",
        "bend_s",
        "bezier",
        "circle",
        "coupler_straight",
        "cross",
        "ellipse",
        "rectangle",
        "regular_polygon",
        "ring",
        "straight",
        "taper",
        "triangle",
    }
)

RAW_POLYGON_CALLS = frozenset({"add_polygon", "from_polygon"})
IMAGE_IMPORT_PREFIXES = (
    "PIL",
    "cv2",
    "imageio",
    "skimage",
    "matplotlib.image",
)
FORBIDDEN_DYNAMIC_CALLS = frozenset({"compile", "eval", "exec", "__import__"})


def _is_image_module(name: str) -> bool:
    """Segment-aware prefix match: ``PIL.Image`` yes, ``PILLOW`` no."""
    return any(name == p or name.startswith(p + ".") for p in IMAGE_IMPORT_PREFIXES)
COORDINATE_TUPLE_LIMIT = 256
NUMERIC_LITERAL_LIMIT = 1024


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


def _is_number(node: ast.expr) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        node = node.operand
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float))


def purity_violations(source: str) -> list[str]:
    """Return source-policy violations without executing ``source``.

    The analysis follows aliases for ``gdsfactory`` and its component namespace,
    rejects non-catalog components and dynamic component lookup, and blocks the
    raster-tracing/raw-polygon escape hatches covered by the public admission
    policy.
    """

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"syntax-error: {exc.msg}"]

    gf_aliases: set[str] = {"gf", "gdsfactory"}
    component_aliases: set[str] = set()
    imported_components: dict[str, str] = {}
    hits: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                if alias.name == "gdsfactory":
                    gf_aliases.add(bound)
                elif alias.name == "gdsfactory.components":
                    component_aliases.add(alias.asname or "components")
                if _is_image_module(alias.name):
                    hits.append(f"image-read import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _is_image_module(module):
                hits.append(f"image-read import: {module}")
            if module == "gdsfactory":
                for alias in node.names:
                    if alias.name in {"components", "c"}:
                        component_aliases.add(alias.asname or alias.name)
            elif module == "gdsfactory.components":
                for alias in node.names:
                    if alias.name == "*":
                        hits.append("non-catalog component import: wildcard")
                        continue
                    imported_components[alias.asname or alias.name] = alias.name
                    if alias.name not in ALLOWED_COMPONENTS:
                        hits.append(f"non-catalog component import: {alias.name}")

    def is_component_namespace(node: ast.AST) -> bool:
        return (isinstance(node, ast.Name) and node.id in component_aliases) or (
            isinstance(node, ast.Attribute)
            and node.attr in {"components", "c"}
            and isinstance(node.value, ast.Name)
            and node.value.id in gf_aliases
        )

    component_callables = dict(imported_components)
    assignments = [
        node for node in ast.walk(tree) if isinstance(node, (ast.Assign, ast.AnnAssign))
    ]
    for _ in range(len(assignments) + 1):
        changed = False
        for node in assignments:
            value = node.value
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [target.id for target in targets if isinstance(target, ast.Name)]
            if not names or value is None:
                continue
            if isinstance(value, ast.Name) and value.id in gf_aliases:
                for name in names:
                    if name not in gf_aliases:
                        gf_aliases.add(name)
                        changed = True
            elif is_component_namespace(value):
                for name in names:
                    if name not in component_aliases:
                        component_aliases.add(name)
                        changed = True
            elif isinstance(value, ast.Attribute) and is_component_namespace(
                value.value
            ):
                for name in names:
                    if component_callables.get(name) != value.attr:
                        component_callables[name] = value.attr
                        changed = True
            elif isinstance(value, ast.Name) and value.id in component_callables:
                for name in names:
                    component = component_callables[value.id]
                    if component_callables.get(name) != component:
                        component_callables[name] = component
                        changed = True
        if not changed:
            break

    tuple_count = 0
    numeric_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            numeric_count += 1
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            tuple_count += sum(
                1
                for item in node.elts
                if isinstance(item, (ast.Tuple, ast.List))
                and len(item.elts) >= 2
                and all(_is_number(value) for value in item.elts)
            )
        if isinstance(node, ast.Attribute):
            if node.attr in RAW_POLYGON_CALLS:
                hits.append(node.attr)
            if (
                is_component_namespace(node.value)
                and node.attr not in ALLOWED_COMPONENTS
            ):
                hits.append(f"non-catalog component: {_dotted_name(node) or node.attr}")
        if not isinstance(node, ast.Call):
            continue
        name = _dotted_name(node.func)
        leaf = name.rsplit(".", 1)[-1] if name else None
        if leaf in RAW_POLYGON_CALLS:
            hits.append(str(leaf))
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_DYNAMIC_CALLS:
            hits.append(f"dynamic execution: {node.func.id}")
        if leaf in {"open", "imread"} and (
            leaf == "imread" or (name and name.endswith("Image.open"))
        ):
            hits.append(f"image-read call: {name}")
        if isinstance(node.func, ast.Name):
            component = component_callables.get(node.func.id)
            if component and component not in ALLOWED_COMPONENTS:
                hits.append(f"non-catalog component: {component}")
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and node.args
            and (
                is_component_namespace(node.args[0])
                or (
                    isinstance(node.args[0], ast.Name)
                    and node.args[0].id in gf_aliases
                )
            )
        ):
            hits.append("dynamic component resolution")
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "vars"
            and node.args
            and is_component_namespace(node.args[0])
        ):
            hits.append("dynamic component mapping access")
        if name and any(name == f"{alias}.get_component" for alias in gf_aliases):
            hits.append("dynamic component resolver: get_component")

    if tuple_count >= COORDINATE_TUPLE_LIMIT:
        hits.append(f"coordinate-dump: {tuple_count} literal coordinate tuples")
    if numeric_count >= NUMERIC_LITERAL_LIMIT:
        hits.append(f"numeric-dump: {numeric_count} numeric literals")
    # Textual belt (parity with the pre-extraction gate): a raw-polygon token
    # anywhere in the source rejects, closing the getattr(obj, "add_polygon")
    # string-literal escape the AST walk cannot see.
    for name in sorted(RAW_POLYGON_CALLS):
        if re.search(rf"\b{name}\b", source):
            hits.append(name)
    return list(dict.fromkeys(hits))
