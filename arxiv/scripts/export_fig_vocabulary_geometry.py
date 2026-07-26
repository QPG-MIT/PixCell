"""Export exact GDSFactory geometry for the Wolfram figure compositor.

The JSON contains only measured geometry and metadata.  Mathematica controls
layout and annotation, but never redraws or approximates the device bodies.

Run:
    .venv/bin/python arxiv/scripts/export_fig_vocabulary_geometry.py OUTPUT.json
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path
from typing import Any

import gdstk
import gdsfactory as gf
import numpy as np
from homi.conductor.gate import _CATALOG_COMPONENTS


REPO = Path(__file__).resolve().parents[2]
PINNED_GDSFACTORY = "9.20.7"
LAYER = (1, 0)
SEMANTIC_LAYERS = {
    "straight": (10, 0),
    "bend": (20, 0),
    "coupler": (30, 0),
}

if version("gdsfactory") != PINNED_GDSFACTORY:
    raise RuntimeError(
        f"Paper figures require gdsfactory {PINNED_GDSFACTORY}; "
        f"found {version('gdsfactory')}."
    )


def _polygons_by_layer(
    component: gf.Component,
) -> dict[tuple[int, int], list[np.ndarray]]:
    """Flatten a component through GDS and return polygon points by layer."""
    temporary = tempfile.NamedTemporaryFile(suffix=".gds", delete=False)
    temporary.close()
    try:
        component.write_gds(temporary.name, with_metadata=False)
        library = gdstk.read_gds(temporary.name)
        output: dict[tuple[int, int], list[np.ndarray]] = {}
        for top in library.top_level():
            top.flatten()
            for polygon in top.polygons:
                key = (int(polygon.layer), int(polygon.datatype))
                output.setdefault(key, []).append(
                    np.asarray(polygon.points, dtype=float)
                )
        return output
    finally:
        os.unlink(temporary.name)


def _polygons(component: gf.Component) -> list[np.ndarray]:
    return [
        polygon
        for layer_polygons in _polygons_by_layer(component).values()
        for polygon in layer_polygons
    ]


XS = gf.cross_section.cross_section(width=0.5, layer=LAYER)

BASIC = [
    ("rectangle", gf.components.rectangle(size=(10, 5), layer=LAYER, centered=True)),
    ("circle", gf.components.circle(radius=5, layer=LAYER)),
    ("ellipse", gf.components.ellipse(radii=(7, 4), layer=LAYER)),
    ("ring", gf.components.ring(width=1, radius=5, layer=LAYER)),
    ("cross", gf.components.cross(length=10, width=3, layer=LAYER)),
    ("triangle", gf.components.triangle(x=10, y=8, layer=LAYER)),
    (
        "regular_polygon",
        gf.components.regular_polygon(sides=6, side_length=5, layer=LAYER),
    ),
    ("L", gf.components.L(width=3, size=(10, 12), layer=LAYER)),
]

WAVEGUIDES = [
    ("straight", gf.components.straight(length=12, cross_section=XS)),
    (
        "bend_euler",
        gf.components.bend_euler(radius=10, angle=90, cross_section=XS),
    ),
    (
        "bend_circular",
        gf.components.bend_circular(radius=10, angle=90, cross_section=XS),
    ),
    ("bend_s", gf.components.bend_s(size=(20, 5), cross_section=XS)),
    (
        "taper",
        gf.components.taper(length=10, width1=0.5, width2=2.0, layer=LAYER),
    ),
    (
        "coupler_straight",
        gf.components.coupler_straight(
            length=10,
            gap=0.3,
            cross_section=XS,
        ),
    ),
]

assert {name for name, _component in BASIC} | {
    name for name, _component in WAVEGUIDES
} == set(
    _CATALOG_COMPONENTS
), "Figure 1 must match the conductor's component whitelist."

PATHS = [
    ("Path", gf.Path([(0, 0), (4, 0), (7, 3), (11, 1)])),
    ("path.straight", gf.path.straight(length=12)),
    ("path.arc", gf.path.arc(radius=8, angle=115)),
    ("path.euler", gf.path.euler(radius=8, angle=95, p=0.5)),
    (
        "path.smooth",
        gf.path.smooth(
            points=[(0, 0), (4, 0), (7, 3), (11, 3), (14, 0)],
            radius=2.5,
        ),
    ),
    (
        "path.spiral",
        gf.path.spiral_archimedean(
            min_bend_radius=4,
            separation=1.8,
            number_of_loops=1.6,
            npoints=160,
        ),
    ),
]


def _boolean_polygons(operation: str) -> list[np.ndarray]:
    rectangle = gdstk.rectangle((-5, -4), (5, 4), layer=1)
    circle = gdstk.ellipse((3, 0), 4, layer=1)
    return [
        np.asarray(polygon.points, dtype=float)
        for polygon in gdstk.boolean(
            [rectangle],
            [circle],
            operation,
            layer=1,
        )
    ]


def _cross_section(width: float, layer: tuple[int, int]) -> gf.CrossSection:
    return gf.cross_section.cross_section(width=width, layer=layer)


def _build_coupler(
    *,
    width: float = 0.50,
    gap: float = 0.25,
    coupling_length: float = 10.0,
    bend_length: float = 18.0,
    offset: float = 3.0,
    straight_length: float = 8.0,
    semantic_layers: bool = False,
) -> tuple[gf.Component, dict[str, object]]:
    """Build a symmetric four-port coupler from catalog components."""
    layers = (
        SEMANTIC_LAYERS
        if semantic_layers
        else {
            "straight": LAYER,
            "bend": LAYER,
            "coupler": LAYER,
        }
    )
    straight_xs = _cross_section(width, layers["straight"])
    bend_xs = _cross_section(width, layers["bend"])
    coupler_xs = _cross_section(width, layers["coupler"])

    component = gf.Component()
    coupling = component << gf.components.coupler_straight(
        length=coupling_length,
        gap=gap,
        cross_section=coupler_xs,
    )

    lower_left = component << gf.components.bend_s(
        size=(bend_length, +offset),
        cross_section=bend_xs,
    )
    lower_left.connect(
        "o2",
        coupling.ports["o1"],
        allow_layer_mismatch=semantic_layers,
    )
    upper_left = component << gf.components.bend_s(
        size=(bend_length, -offset),
        cross_section=bend_xs,
    )
    upper_left.connect(
        "o2",
        coupling.ports["o2"],
        allow_layer_mismatch=semantic_layers,
    )
    lower_right = component << gf.components.bend_s(
        size=(bend_length, -offset),
        cross_section=bend_xs,
    )
    lower_right.connect(
        "o1",
        coupling.ports["o4"],
        allow_layer_mismatch=semantic_layers,
    )
    upper_right = component << gf.components.bend_s(
        size=(bend_length, +offset),
        cross_section=bend_xs,
    )
    upper_right.connect(
        "o1",
        coupling.ports["o3"],
        allow_layer_mismatch=semantic_layers,
    )

    left_lower_straight = component << gf.components.straight(
        length=straight_length,
        cross_section=straight_xs,
    )
    left_lower_straight.connect(
        "o2",
        lower_left.ports["o1"],
        allow_layer_mismatch=semantic_layers,
    )
    left_upper_straight = component << gf.components.straight(
        length=straight_length,
        cross_section=straight_xs,
    )
    left_upper_straight.connect(
        "o2",
        upper_left.ports["o1"],
        allow_layer_mismatch=semantic_layers,
    )
    right_lower_straight = component << gf.components.straight(
        length=straight_length,
        cross_section=straight_xs,
    )
    right_lower_straight.connect(
        "o1",
        lower_right.ports["o2"],
        allow_layer_mismatch=semantic_layers,
    )
    right_upper_straight = component << gf.components.straight(
        length=straight_length,
        cross_section=straight_xs,
    )
    right_upper_straight.connect(
        "o1",
        upper_right.ports["o2"],
        allow_layer_mismatch=semantic_layers,
    )

    component.add_port("o1", port=left_lower_straight.ports["o1"])
    component.add_port("o2", port=left_upper_straight.ports["o1"])
    component.add_port("o3", port=right_upper_straight.ports["o2"])
    component.add_port("o4", port=right_lower_straight.ports["o2"])

    center_separation = gap + width
    metadata: dict[str, object] = {
        "ports": {
            port.name: tuple(port.dcenter)
            for port in component.ports
        },
        "connections": [
            (-bend_length, -offset),
            (-bend_length, center_separation + offset),
            (0.0, 0.0),
            (0.0, center_separation),
            (coupling_length, 0.0),
            (coupling_length, center_separation),
            (coupling_length + bend_length, -offset),
            (coupling_length + bend_length, center_separation + offset),
        ],
        "coupling_span": (0.0, coupling_length),
        "gap_edges": (
            width / 2.0,
            center_separation - width / 2.0,
        ),
        "xlim": (
            -bend_length - straight_length,
            coupling_length + bend_length + straight_length,
        ),
    }
    assert len(component.insts) == 9
    assert len(component.ports) == 4
    return component, metadata


def _points(values: np.ndarray) -> list[list[float]]:
    return [[round(float(x), 6), round(float(y), 6)] for x, y in values]


def _component(component: gf.Component) -> dict[str, Any]:
    return {
        "polygons": [_points(polygon) for polygon in _polygons(component)],
        "ports": [
            {
                "name": port.name,
                "center": [round(float(v), 6) for v in port.dcenter],
            }
            for port in component.ports
        ],
    }


def _metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _metadata(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_metadata(item) for item in value]
    if isinstance(value, np.ndarray):
        return _metadata(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    return value


def _waveguide_chain() -> dict[str, Any]:
    """A literal three-instance port-connected chain for Figure 1b."""
    component = gf.Component()
    straight_xs = gf.cross_section.cross_section(width=0.5, layer=(10, 0))
    bend_xs = gf.cross_section.cross_section(width=0.5, layer=(20, 0))

    straight = component << gf.components.straight(
        length=8.0,
        cross_section=straight_xs,
    )
    bend = component << gf.components.bend_euler(
        radius=10.0,
        angle=90.0,
        cross_section=bend_xs,
    )
    bend.connect("o1", straight.ports["o2"], allow_layer_mismatch=True)
    taper = component << gf.components.taper(
        length=7.0,
        width1=0.5,
        width2=1.2,
        layer=(30, 0),
    )
    taper.connect("o1", bend.ports["o2"], allow_layer_mismatch=True)

    component.add_port("o1", port=straight.ports["o1"])
    component.add_port("o2", port=taper.ports["o2"])
    assert len(component.insts) == 3
    assert len(component.ports) == 2
    polygons_by_layer = _polygons_by_layer(component)
    return {
        "groups": {
            "straight": [
                _points(polygon) for polygon in polygons_by_layer.get((10, 0), [])
            ],
            "bend_euler": [
                _points(polygon) for polygon in polygons_by_layer.get((20, 0), [])
            ],
            "taper": [
                _points(polygon) for polygon in polygons_by_layer.get((30, 0), [])
            ],
        },
        "ports": [
            {
                "name": port.name,
                "center": [round(float(value), 6) for value in port.dcenter],
            }
            for port in component.ports
        ],
        "connections": [
            [round(float(value), 6) for value in straight.ports["o2"].dcenter],
            [round(float(value), 6) for value in bend.ports["o2"].dcenter],
        ],
    }


def _figure_one() -> dict[str, Any]:
    demo_path = gf.path.smooth(
        points=[(0, 0), (4, 0), (7, 2.6), (11, 2.6), (14, 0)],
        radius=2.2,
    )
    narrow_xs = gf.cross_section.cross_section(width=0.25, layer=LAYER)
    wide_xs = gf.cross_section.cross_section(width=1.25, layer=LAYER)
    transition = gf.path.transition(narrow_xs, wide_xs, width_type="sine")
    constant_body = gf.path.extrude(demo_path, cross_section=XS)
    variable_body = gf.path.extrude_transition(demo_path, transition)
    boolean_rectangle = gdstk.rectangle((-5, -4), (5, 4), layer=1)
    boolean_circle = gdstk.ellipse((3, 0), 4, layer=1)

    def boolean_polygons(
        first: gdstk.Polygon,
        second: gdstk.Polygon,
        operation: str,
    ) -> list[list[list[float]]]:
        return [
            _points(np.asarray(polygon.points, dtype=float))
            for polygon in gdstk.boolean(
                [first],
                [second],
                operation,
                layer=1,
            )
        ]

    return {
        "basic": [
            {"name": name, **_component(component)}
            for name, component in BASIC
        ],
        "waveguides": [
            {"name": name, **_component(component)}
            for name, component in WAVEGUIDES
        ],
        "paths": [
            {"name": name, "points": _points(np.asarray(path.points, dtype=float))}
            for name, path in PATHS
        ],
        "demo_path": _points(np.asarray(demo_path.points, dtype=float)),
        "constant_body": _component(constant_body),
        "variable_body": _component(variable_body),
        "waveguide_chain": _waveguide_chain(),
        "boolean_inputs": {
            "A": _points(np.asarray(boolean_rectangle.points, dtype=float)),
            "B": _points(np.asarray(boolean_circle.points, dtype=float)),
        },
        "boolean_partitions": {
            "A_only": boolean_polygons(
                boolean_rectangle,
                boolean_circle,
                "not",
            ),
            "intersection": boolean_polygons(
                boolean_rectangle,
                boolean_circle,
                "and",
            ),
            "B_only": boolean_polygons(
                boolean_circle,
                boolean_rectangle,
                "not",
            ),
        },
        "booleans": [
            {
                "operation": operation,
                "polygons": [
                    _points(polygon)
                    for polygon in _boolean_polygons(operation)
                ],
            }
            for operation in ("or", "and", "not", "xor")
        ],
    }


def _figure_two() -> dict[str, Any]:
    base_params = {
        "width": 0.50,
        "gap": 0.25,
        "coupling_length": 10.0,
        "bend_length": 18.0,
        "offset": 3.0,
        "straight_length": 8.0,
    }
    retuned_params = dict(base_params, gap=0.75, coupling_length=16.0)
    midpoint_params = dict(base_params, gap=0.50, coupling_length=13.0)

    semantic_component, semantic_meta = _build_coupler(
        **base_params, semantic_layers=True
    )
    retuned_semantic_component, _ = _build_coupler(
        **retuned_params, semantic_layers=True
    )
    base_component, base_meta = _build_coupler(**base_params)
    midpoint_component, midpoint_meta = _build_coupler(**midpoint_params)
    retuned_component, retuned_meta = _build_coupler(**retuned_params)
    polygons_by_layer = _polygons_by_layer(semantic_component)
    retuned_polygons_by_layer = _polygons_by_layer(
        retuned_semantic_component
    )

    primitives = [
        {
            "name": "straight",
            "parameters": "Ls",
            "count": 4,
            **_component(gf.components.straight(length=8, cross_section=XS)),
        },
        {
            "name": "bend_s",
            "parameters": "Lb, +/-dy",
            "count": 4,
            **_component(gf.components.bend_s(size=(18, 3), cross_section=XS)),
            "negative": _component(
                gf.components.bend_s(size=(18, -3), cross_section=XS)
            ),
        },
        {
            "name": "coupler_straight",
            "parameters": "Lc, g",
            "count": 1,
            **_component(
                gf.components.coupler_straight(
                    length=10,
                    gap=0.25,
                    cross_section=XS,
                )
            ),
        },
    ]

    semantic_groups = {
        name: [_points(polygon) for polygon in polygons_by_layer.get(layer, [])]
        for name, layer in SEMANTIC_LAYERS.items()
    }
    retuned_semantic_groups = {
        name: [
            _points(polygon)
            for polygon in retuned_polygons_by_layer.get(layer, [])
        ]
        for name, layer in SEMANTIC_LAYERS.items()
    }

    return {
        "parameters": base_params,
        "primitives": primitives,
        "semantic_groups": semantic_groups,
        "retuned_semantic_groups": retuned_semantic_groups,
        "semantic_meta": _metadata(semantic_meta),
        "base": _component(base_component),
        "base_meta": _metadata(base_meta),
        "midpoint": _component(midpoint_component),
        "midpoint_meta": _metadata(midpoint_meta),
        "retuned": _component(retuned_component),
        "retuned_meta": _metadata(retuned_meta),
    }


def main() -> None:
    output = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else REPO / "tmp" / "pdfs" / "fig-vocabulary-geometry.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "gdsfactory_version": PINNED_GDSFACTORY,
        "figure1": _figure_one(),
        "figure2": _figure_two(),
    }
    output.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
