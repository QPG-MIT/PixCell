"""Shared, dependency-light helpers for the PixCell dataset release tools.

This module is ordinary tooling, not a Hugging Face loading script.  The
published Parquet files are the loader-free canonical dataset.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from skimage.transform import resize


SCHEMA_VERSION = "pixcell-image-code-curriculum-v1"
LEVELS = ("l0", "l1", "l2", "l3", "l4")
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
COORDINATE_TUPLE_LIMIT = 256
NUMERIC_LITERAL_LIMIT = 1024
ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"/" r"Users/[^/\s]+/"),
    re.compile(r"/" r"home/[^/\s]+/"),
    re.compile(r"[A-Za-z]:\\\\" r"Users\\\\[^\\\\\s]+\\\\"),
)
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
SAFE_PUBLIC_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
FORBIDDEN_RELEASE_IMPORT_ROOTS = frozenset(
    {"tasks", "env", "rl", "homi", "michaelangelo"}
)
HOST_CONTROL_FILES = frozenset({".gitattributes", ".gitignore", ".gitkeep"})


class ReleaseError(RuntimeError):
    """Raised when a release invariant is violated."""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


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
    """Enforce the public PixCell primitive catalog by AST analysis."""

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
                if alias.name.startswith(IMAGE_IMPORT_PREFIXES):
                    hits.append(f"image-read import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith(IMAGE_IMPORT_PREFIXES):
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
                    isinstance(node.args[0], ast.Name) and node.args[0].id in gf_aliases
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
    return list(dict.fromkeys(hits))


def primitive_calls(source: str) -> list[str]:
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _dotted_name(node.func)
        if not name:
            continue
        if ".components." in name:
            found.add(name.rsplit(".", 1)[-1])
        elif ".path." in name:
            found.add(f"path.{name.rsplit('.', 1)[-1]}")
        elif name.endswith(".boolean") or name == "gf.boolean":
            found.add("boolean")
        elif name.endswith(".extrude_transition"):
            found.add("extrude_transition")
        elif name.endswith(".extrude"):
            found.add("extrude")
    return sorted(found)


def forbidden_release_imports(source: str) -> list[str]:
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        for module in modules:
            root = module.split(".", 1)[0]
            if root in FORBIDDEN_RELEASE_IMPORT_ROOTS:
                found.add(module)
    return sorted(found)


def top_level_parameters(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    values: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if len(targets) != 1 or not isinstance(targets[0], ast.Name):
            continue
        try:
            values[targets[0].id] = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
    return values


def scan_text(label: str, text: str) -> list[str]:
    hits: list[str] = []
    for pattern in ABSOLUTE_PATH_PATTERNS:
        if pattern.search(text):
            hits.append(f"{label}: absolute developer path")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            hits.append(f"{label}: possible secret")
    return hits


def scan_value_strings(label: str, value: Any) -> list[str]:
    hits: list[str] = []
    for text in flatten_strings(value):
        hits.extend(scan_text(label, text))
    return list(dict.fromkeys(hits))


def normalized_d4_sha256(image: Image.Image, size: int = 192, margin: int = 6) -> str:
    array = np.asarray(image.convert("L"))
    mask = array < 245
    if not mask.any():
        raise ReleaseError("image contains no foreground material")
    ys, xs = np.nonzero(mask)
    crop = mask[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    available = size - 2 * margin
    scale = min(available / crop.shape[0], available / crop.shape[1])
    height = max(1, min(available, int(round(crop.shape[0] * scale))))
    width = max(1, min(available, int(round(crop.shape[1] * scale))))
    fitted = (
        resize(
            crop.astype(np.uint8),
            (height, width),
            order=0,
            mode="constant",
            preserve_range=True,
            anti_aliasing=False,
        )
        >= 0.5
    )
    canvas = np.zeros((size, size), dtype=bool)
    x0 = (size - width) // 2
    y0 = (size - height) // 2
    canvas[y0 : y0 + height, x0 : x0 + width] = fitted
    variants: list[np.ndarray] = []
    for turns in range(4):
        rotated = np.rot90(canvas, turns)
        variants.extend((rotated, np.fliplr(rotated)))
    return min(sha256_bytes(item.tobytes()) for item in variants)


def no_absolute_path(value: Any, *, label: str) -> None:
    text = canonical_json(value) if not isinstance(value, str) else value
    hits = scan_text(label, text)
    if hits:
        raise ReleaseError("; ".join(hits))


def iter_release_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "checksums.sha256":
            continue
        if path.name in HOST_CONTROL_FILES:
            continue
        if any(
            part in {"__pycache__", ".pytest_cache", ".ruff_cache", ".git"}
            for part in path.parts
        ):
            continue
        yield path


def write_checksums(root: Path) -> None:
    target = root / "metadata" / "checksums.sha256"
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{sha256_file(path)}  {path.relative_to(root).as_posix()}"
        for path in iter_release_files(root)
    ]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_checksums(root: Path) -> None:
    path = root / "metadata" / "checksums.sha256"
    if not path.is_file():
        raise ReleaseError("metadata/checksums.sha256 is missing")
    expected: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        expected[relative] = digest
    actual = {
        item.relative_to(root).as_posix(): sha256_file(item)
        for item in iter_release_files(root)
    }
    if expected != actual:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        changed = sorted(
            key for key in set(expected) & set(actual) if expected[key] != actual[key]
        )
        raise ReleaseError(
            f"checksum inventory drifted: missing={missing}, extra={extra}, "
            f"changed={changed}"
        )


def flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from flatten_strings(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from flatten_strings(child)
