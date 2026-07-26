#!/usr/bin/env python3
"""Primitive-built visual prototypes for PixCell expansion review.

These scenes are proposal evidence, not admitted dataset programs.  They use
only the public PixCell primitive vocabulary to make every proposed grammar
visually inspectable before any row is generated or admitted.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

import gdsfactory as gf
import numpy as np
from PIL import Image, ImageDraw

from _shared import ReleaseError, normalized_d4_sha256


LAYER = (1, 0)
VOID_LAYER = (2, 0)
CANVAS_SIZE = (720, 540)
CANVAS_MARGIN = 34
ANTIALIAS = 2


@dataclass(frozen=True)
class RenderedProposalScene:
    """One maximum-visibility proposal raster and its geometric witnesses."""

    image: Image.Image
    bbox_um: tuple[tuple[float, float], tuple[float, float]]
    display_scale_px_per_um: tuple[float, float]
    port_count: int
    port_names: tuple[str, ...]
    normalized_d4_sha256: str


def _xs(width: float) -> gf.CrossSection:
    return gf.cross_section.cross_section(width=width, layer=LAYER)


def _segment(
    component: gf.Component,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    width: float = 3.2,
    round_ends: bool = False,
) -> None:
    x0, y0 = start
    x1, y1 = end
    length = math.hypot(x1 - x0, y1 - y0)
    if length <= 1e-6:
        return
    ref = component << gf.components.straight(
        length=length,
        cross_section=_xs(width),
    )
    ref.rotate(math.degrees(math.atan2(y1 - y0, x1 - x0)))
    ref.move((x0, y0))
    if round_ends:
        for x, y in (start, end):
            dot = component << gf.components.circle(
                radius=width / 2,
                layer=LAYER,
            )
            dot.move((x, y))


def _polyline(
    component: gf.Component,
    points: list[tuple[float, float]],
    *,
    width: float = 3.2,
    round_joints: bool = True,
) -> None:
    for start, end in zip(points, points[1:]):
        _segment(component, start, end, width=width)
    if round_joints:
        for x, y in points[1:-1]:
            joint = component << gf.components.circle(
                radius=width / 2,
                layer=LAYER,
            )
            joint.move((x, y))


def _s_curve(
    component: gf.Component,
    start: tuple[float, float],
    *,
    dx: float,
    dy: float,
    width: float = 3.2,
) -> None:
    x0, y0 = start
    ref = component << gf.components.bend_s(
        size=(dx, dy),
        cross_section=_xs(width),
        allow_min_radius_violation=True,
    )
    ref.move((x0, y0))


def _bezier(
    component: gf.Component,
    start: tuple[float, float],
    *,
    dx: float,
    dy: float,
    width: float = 3.2,
    hook: float = 0.0,
) -> None:
    x0, y0 = start
    ref = component << gf.components.bezier(
        control_points=(
            (0.0, 0.0),
            (0.34 * dx, hook),
            (0.68 * dx, dy - hook),
            (dx, dy),
        ),
        cross_section=_xs(width),
        allow_min_radius_violation=True,
    )
    ref.move((x0, y0))


def _cubic_bezier_points(
    control_points: tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ],
    *,
    count: int = 96,
) -> list[tuple[float, float]]:
    """Sample one cubic Bezier for use inside a compound path."""

    values = np.linspace(0.0, 1.0, count)
    points = []
    p0, p1, p2, p3 = control_points
    for value in values:
        inverse = 1.0 - value
        x = (
            inverse**3 * p0[0]
            + 3 * inverse**2 * value * p1[0]
            + 3 * inverse * value**2 * p2[0]
            + value**3 * p3[0]
        )
        y = (
            inverse**3 * p0[1]
            + 3 * inverse**2 * value * p1[1]
            + 3 * inverse * value**2 * p2[1]
            + value**3 * p3[1]
        )
        points.append((float(x), float(y)))
    return points


def _compound_path(
    component: gf.Component,
    points: list[tuple[float, float]],
    *,
    width: float,
    arc_radius: float,
    arc_angle: float,
    straight_length: float,
    start: tuple[float, float] = (0.0, 0.0),
) -> tuple[float, float]:
    """Extrude one connected polyline/Bezier → arc → straight sequence."""

    path = gf.Path(points)
    path.append(gf.path.arc(radius=arc_radius, angle=arc_angle))
    path.append(gf.path.straight(length=straight_length))
    ref = component << gf.path.extrude(path, cross_section=_xs(width))
    ref.move(start)
    return (
        float(path.points[-1][0]) + start[0],
        float(path.points[-1][1]) + start[1],
    )


def _rectangle(
    component: gf.Component,
    center: tuple[float, float],
    size: tuple[float, float],
) -> None:
    ref = component << gf.components.rectangle(
        size=size,
        layer=LAYER,
        centered=True,
        port_type=None,
    )
    ref.move(center)


def _rotated_rectangle(
    component: gf.Component,
    center: tuple[float, float],
    size: tuple[float, float],
    rotation: float,
) -> None:
    """Place one primitive rectangle with an explicit orientation."""

    ref = component << gf.components.rectangle(
        size=size,
        layer=LAYER,
        centered=True,
        port_type=None,
    )
    ref.rotate(rotation)
    ref.move(center)


def _ellipse(
    component: gf.Component,
    center: tuple[float, float],
    radii: tuple[float, float],
) -> None:
    ref = component << gf.components.ellipse(radii=radii, layer=LAYER)
    ref.move(center)


def _circle(component: gf.Component, center: tuple[float, float], radius: float) -> None:
    ref = component << gf.components.circle(radius=radius, layer=LAYER)
    ref.move(center)


def _void_circle(
    component: gf.Component,
    center: tuple[float, float],
    radius: float,
) -> None:
    """Place a proposal-renderer void primitive on the dedicated erase layer."""

    ref = component << gf.components.circle(radius=radius, layer=VOID_LAYER)
    ref.move(center)


def _ring(
    component: gf.Component,
    center: tuple[float, float],
    radius: float,
    *,
    width: float = 3.0,
    angle: float = 360.0,
    rotation: float = 0.0,
) -> None:
    ref = component << gf.components.ring(
        radius=radius,
        width=width,
        angle=angle,
        layer=LAYER,
    )
    if rotation:
        ref.rotate(rotation)
    ref.move(center)


def _taper(
    component: gf.Component,
    start: tuple[float, float],
    *,
    length: float,
    width1: float,
    width2: float,
    rotation: float = 0.0,
) -> None:
    ref = component << gf.components.taper(
        length=length,
        width1=width1,
        width2=width2,
        layer=LAYER,
    )
    if rotation:
        ref.rotate(rotation)
    ref.move(start)


def _teeth(
    component: gf.Component,
    *,
    x0: float,
    y: float,
    count: int,
    pitch: float,
    width: float,
    heights: list[float] | None = None,
    bilateral: bool = False,
    stagger: bool = False,
) -> None:
    for index in range(count):
        height = heights[index] if heights is not None else 8.0
        x = x0 + index * pitch
        signs = (-1, 1) if bilateral else (1,)
        for sign in signs:
            offset = 0.5 * pitch if stagger and sign < 0 else 0.0
            _rectangle(
                component,
                (x + offset, y + sign * (height / 2 + 1.0)),
                (width, height),
            )


def _parse_signature(value: Any) -> tuple[int, int]:
    text = str(value)
    pieces = text.lower().split("x")
    if len(pieces) != 2:
        raise ReleaseError(f"invalid proposal port signature: {text}")
    try:
        inputs, outputs = (int(piece) for piece in pieces)
    except ValueError as exc:
        raise ReleaseError(f"invalid proposal port signature: {text}") from exc
    if min(inputs, outputs) < 0 or inputs + outputs < 1:
        raise ReleaseError(f"invalid proposal port signature: {text}")
    return inputs, outputs


def _spread(count: int, *, pitch: float = 13.0) -> list[float]:
    if count == 0:
        return []
    center = (count - 1) / 2
    return [(index - center) * pitch for index in range(count)]


def _boundary_ports(
    component: gf.Component,
    *,
    inputs: int,
    outputs: int,
    x_left: float,
    x_right: float,
    left_ys: list[float] | None = None,
    right_ys: list[float] | None = None,
    width: float = 3.2,
) -> tuple[str, ...]:
    left = left_ys if left_ys is not None else _spread(inputs)
    right = right_ys if right_ys is not None else _spread(outputs)
    if len(left) != inputs or len(right) != outputs:
        raise ReleaseError("proposal scene port placement does not match signature")
    names: list[str] = []
    for index, y in enumerate(left, start=1):
        name = f"o{len(names) + 1}"
        component.add_port(
            name=name,
            center=(x_left, y),
            width=width,
            orientation=180.0,
            layer=LAYER,
            port_type="optical",
        )
        names.append(name)
    for index, y in enumerate(right, start=1):
        del index
        name = f"o{len(names) + 1}"
        component.add_port(
            name=name,
            center=(x_right, y),
            width=width,
            orientation=0.0,
            layer=LAYER,
            port_type="optical",
        )
        names.append(name)
    return tuple(names)


def _connect_terminal_banks(
    component: gf.Component,
    *,
    inputs: int,
    outputs: int,
    x_left: float,
    x_body_left: float,
    x_body_right: float,
    x_right: float,
    body_ys: list[float],
    width: float = 3.2,
) -> tuple[list[float], list[float]]:
    left_ys = _spread(inputs)
    right_ys = _spread(outputs)
    for index, y in enumerate(left_ys):
        target = body_ys[index % len(body_ys)]
        _bezier(
            component,
            (x_left, y),
            dx=x_body_left - x_left + 1.5,
            dy=target - y,
            width=width,
        )
    for index, y in enumerate(right_ys):
        source = body_ys[index % len(body_ys)]
        _bezier(
            component,
            (x_body_right - 1.5, source),
            dx=x_right - x_body_right + 1.5,
            dy=y - source,
            width=width,
        )
    return left_ys, right_ys


def _l1_underbridged_operation(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    del spec
    if variant == 0:
        _bezier(component, (0, -10), dx=58, dy=22, width=4.0, hook=15)
        _segment(component, (58, 12), (88, 12), width=4.0)
        _circle(component, (58, 12), 2.0)
        return 0, 88, [-10], [12]
    if variant == 1:
        _taper(
            component,
            (0, -12),
            length=20,
            width1=2.8,
            width2=6.0,
        )
        _bezier(component, (20, -12), dx=55, dy=22, width=6.0, hook=10)
        _segment(component, (75, 10), (92, 10), width=6.0)
        return 0, 92, [-12], [10]
    if variant == 2:
        end = _compound_path(
            component,
            _cubic_bezier_points(
                (
                    (0.0, 0.0),
                    (16.0, 0.0),
                    (30.0, 16.0),
                    (45.0, 16.0),
                )
            ),
            width=4.0,
            arc_radius=11.0,
            arc_angle=-95.0,
            straight_length=29.0,
            start=(0.0, -13.0),
        )
        return 0, end[0], [-13], [end[1]]
    if variant == 3:
        end = _compound_path(
            component,
            [(0, -14), (23, -14), (34, 2), (54, 2)],
            width=4.0,
            arc_radius=10.0,
            arc_angle=105.0,
            straight_length=34.0,
        )
        return 0, end[0], [-14], [end[1]]
    if variant == 4:
        points = [(0, -14), (22, -14), (34, -2), (53, -2), (68, 14), (91, 14)]
        for index, (start, end) in enumerate(zip(points, points[1:])):
            _segment(component, start, end, width=2.8 + index * 0.75)
            if index:
                _circle(component, start, (2.8 + index * 0.75) / 2)
        return 0, 91, [-14], [14]
    if variant == 5:
        _polyline(
            component,
            [(0, -18), (19, -18), (31, -4), (50, -4), (62, 17), (88, 17)],
            width=4.0,
        )
        return 0, 88, [-18], [17]
    if variant == 6:
        path = gf.Path()
        path.append(gf.path.straight(22.0))
        path.append(
            gf.path.spiral_archimedean(
                min_bend_radius=5.0,
                separation=7.0,
                number_of_loops=2.0,
                npoints=240,
            )
        )
        path.append(gf.path.straight(24.0))
        component.add_ref(gf.path.extrude(path, cross_section=_xs(3.2)))
        end = path.points[-1]
        return 0, float(end[0]), [0.0], [float(end[1])]
    # Tapered terminals remain separate width-changing primitives, but overlap
    # the spiral endpoints so the intended contacts are visually unambiguous.
    spiral = component << gf.path.extrude(
        p=gf.path.spiral_archimedean(
            min_bend_radius=5.0,
            separation=7.0,
            number_of_loops=2.0,
            npoints=220,
        ),
        cross_section=_xs(3.2),
    )
    spiral.move((44, 0))
    _taper(component, (0, -13), length=25, width1=2.5, width2=5.5)
    _bezier(component, (25, -13), dx=12, dy=9, width=5.5)
    _bezier(component, (59, 4), dx=12, dy=13, width=5.5)
    _taper(
        component,
        (71, 17),
        length=25,
        width1=5.5,
        width2=2.5,
    )
    return 0, 96, [-13], [17]


def _l1_port_operation(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    left = _spread(inputs, pitch=10)
    right = _spread(outputs, pitch=10)
    if variant == 0:
        inner = _spread(2, pitch=8.0)
        rail = component << gf.components.coupler_straight(
            length=50,
            gap=4.0,
            cross_section=_xs(4.0),
        )
        rail.move((16, 0))
        for y, yi in zip(left, inner):
            _bezier(component, (0, y), dx=16, dy=yi - y, width=4.0)
        for yi, y in zip(inner, right):
            _bezier(component, (66, yi), dx=18, dy=y - yi, width=4.0)
    elif variant == 1:
        inner = _spread(2, pitch=7.0)
        for y, yi in zip(left, inner):
            _s_curve(component, (0, y), dx=24, dy=yi - y, width=4.0)
        rail = component << gf.components.coupler_straight(
            length=38,
            gap=3.0,
            cross_section=_xs(4.0),
        )
        rail.move((24, 0))
        for yi, y in zip(inner, right):
            _s_curve(component, (62, yi), dx=24, dy=y - yi, width=4.0)
    elif variant == 2:
        widths = (3.0, 6.0)
        inner = _spread(2, pitch=8.0)
        for index, (y, yi) in enumerate(zip(left, inner)):
            _taper(
                component,
                (0, y),
                length=20,
                width1=widths[index],
                width2=4.5,
            )
            _bezier(component, (20, y), dx=12, dy=yi - y, width=4.5)
        for index, (yi, y) in enumerate(zip(inner, right)):
            _bezier(component, (62, yi), dx=12, dy=y - yi, width=4.5)
            _taper(
                component,
                (74, y),
                length=20,
                width1=4.5,
                width2=widths[index],
            )
        rail = component << gf.components.coupler_straight(
            length=30,
            gap=3.5,
            cross_section=_xs(4.5),
        )
        rail.move((32, 0))
    else:
        # Normalize a spiral's native endpoint tangent with one signed return
        # arc, then append an east-facing lead.  This is one connected path,
        # not a pose-only reflection.
        path = gf.Path()
        path.append(gf.path.straight(22.0))
        path.append(
            gf.path.spiral_archimedean(
                min_bend_radius=5.0,
                separation=7.0,
                number_of_loops=2.0,
                npoints=240,
            )
        )
        correction = (-float(path.end_angle)) % 360.0
        if correction > 180:
            correction -= 360
        path.append(gf.path.arc(radius=10.0, angle=correction))
        path.append(gf.path.straight(28.0))
        shift_x = -float(np.min(path.points[:, 0]))
        ref = component << gf.path.extrude(path, cross_section=_xs(3.4))
        ref.move((shift_x, 0.0))
        end = path.points[-1]
        return (
            shift_x,
            float(end[0]) + shift_x,
            [0.0],
            [float(end[1])],
        )
    return 0, 94 if variant == 2 else 86 if variant == 1 else 84, left, right


def _split_rejoin(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
    *,
    hierarchical: bool,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 126.0 if hierarchical else 100.0
    left = _spread(inputs, pitch=12)
    right = _spread(outputs, pitch=12)
    split_x = 24.0
    join_x = x_right - 24.0
    if not hierarchical and variant == 2:
        # A through carrier sprouts one side branch that returns to the very
        # same junction, creating one lollipop/self-return cycle.
        _segment(component, (0, 0), (100, 0), width=3.4)
        _ellipse(component, (48, 0), (7, 10))
        _polyline(
            component,
            [(48, 7), (48, 23), (68, 31), (82, 19), (68, 7), (48, 7)],
            width=3.0,
        )
        _ring(component, (68, 19), 8, width=2.6, angle=250, rotation=145)
        return x_left, x_right, [0.0], [0.0]
    _ellipse(component, (split_x, 0), (8, 13 if variant != 2 else 18))
    _ellipse(component, (join_x, 0), (8, 13 if variant != 2 else 18))
    for y in left:
        _bezier(component, (x_left, y), dx=split_x - 6, dy=-y, width=3.5)
    arm_count = 2 + (variant == 2) + (variant == 3)
    arm_ys = _spread(arm_count, pitch=13)
    for index, y in enumerate(arm_ys):
        bulge = (index - (arm_count - 1) / 2) * (5.0 if variant == 1 else 2.0)
        points = [
            (split_x + 6, 0),
            (split_x + 20, y + bulge),
            (join_x - 20, y - bulge if variant == 1 else y),
            (join_x - 6, 0),
        ]
        _polyline(component, points, width=3.2 + (0.8 if variant == 1 and index == 0 else 0))
        if hierarchical and variant == 3 and index == arm_count - 1:
            branch_x = (split_x + join_x) / 2
            _polyline(
                component,
                [(branch_x - 10, y), (branch_x, y + 12), (branch_x + 10, y + 12)],
                width=2.8,
            )
    for y in right:
        _bezier(component, (join_x + 6, 0), dx=x_right - join_x - 6, dy=y, width=3.5)
    if hierarchical and variant == 3:
        _ring(component, ((split_x + join_x) / 2, arm_ys[0] - 12), 7, width=2.6)
    return x_left, x_right, left, right


def _coupling_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
    *,
    hierarchical: bool,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 126.0 if hierarchical else 100.0
    left = _spread(inputs, pitch=22)
    right = _spread(outputs, pitch=22)
    if not hierarchical and variant in {0, 1}:
        # Explicit interaction words.  Variant 0 repeats two identical
        # coupling windows; variant 1 visibly opens an uncoupled phase spacer.
        outer = (-12.0, 12.0)
        close = (-3.8, 3.8)
        zones = (
            (18, close),
            (38, outer if variant == 1 else close),
            (60, close),
            (82, outer),
        )
        for rail, y0 in enumerate(outer):
            points = [(0, y0)]
            for x, pair in zones:
                points.append((x, pair[rail]))
            points.append((100, y0))
            _polyline(component, points, width=3.4)
        if variant == 0:
            _rectangle(component, (49, 0), (7, 7))
        else:
            _ring(component, (49, 0), 5.0, width=1.8)
    elif not hierarchical and variant == 2:
        # The middle rail is born after the input fan-in and dies before the
        # output fan-out; it is not a third external terminal.
        for y0, yi in zip((-12.0, 12.0), (-6.0, 6.0), strict=True):
            _s_curve(component, (0, y0), dx=25, dy=yi - y0, width=3.4)
            _segment(component, (25, yi), (75, yi), width=3.4)
            _s_curve(component, (75, yi), dx=25, dy=y0 - yi, width=3.4)
        _taper(component, (34, 0), length=10, width1=1.5, width2=3.0)
        _segment(component, (44, 0), (59, 0), width=3.0)
        _taper(component, (59, 0), length=10, width1=3.0, width2=1.5)
    elif not hierarchical and variant == 3:
        # Concentric curved rails are a distinct coupling representation, not
        # merely a straight coupler with another gap value.
        for y0, peak in ((-11.0, 8.0), (11.0, 28.0)):
            _polyline(
                component,
                [
                    (0, y0),
                    (22, y0),
                    (34, peak - 6),
                    (50, peak),
                    (66, peak - 6),
                    (78, y0),
                    (100, y0),
                ],
                width=3.4,
            )
    elif not hierarchical and variant == 4:
        # One strip nucleates two rails, holds a parallel section, and merges.
        _segment(component, (0, 0), (22, 0), width=4.0)
        for sign in (-1, 1):
            _bezier(component, (22, 0), dx=20, dy=sign * 6.0, width=3.2)
            _segment(component, (42, sign * 6.0), (62, sign * 6.0), width=3.2)
            _bezier(component, (62, sign * 6.0), dx=20, dy=-sign * 6.0, width=3.2)
        _segment(component, (82, 0), (100, 0), width=4.0)
    elif not hierarchical and variant == 5:
        # Two unequal inputs exchange power through an asymmetric window and
        # terminate as one wider rail.
        for y, width in zip((-10.0, 10.0), (3.0, 5.0), strict=True):
            _bezier(component, (0, y), dx=34, dy=-y * 0.55, width=width)
        _segment(component, (34, -4.5), (65, -4.5), width=3.0)
        _segment(component, (34, 4.5), (58, 4.5), width=5.0)
        _taper(component, (58, 4.5), length=11, width1=5.0, width2=1.4)
        _bezier(component, (65, -4.5), dx=22, dy=4.5, width=7.0)
        _segment(component, (87, 0), (100, 0), width=7.0)
    else:
        # L3 interaction systems use longer, zoned windows and may introduce
        # repeated media.  Each variant is refined below by its own visible
        # system-level witness.
        if variant == 0:
            for y0, yi in zip((-13.0, 13.0), (-4.0, 4.0), strict=True):
                _s_curve(component, (0, y0), dx=24, dy=yi - y0, width=3.2)
                _segment(component, (24, yi), (53, yi), width=3.2)
            _polyline(component, [(53, -4), (63, -10), (73, -7)], width=3.2)
            _polyline(component, [(53, 4), (63, 13), (73, 9)], width=3.2)
            _polyline(
                component,
                [(73, -7), (84, 0), (95, 9), (108, 1), (126, -13)],
                width=3.2,
            )
            _polyline(
                component,
                [(73, 9), (84, 18), (95, 28), (108, 21), (126, 13)],
                width=3.2,
            )
            return x_left, x_right, left, right
        if variant == 1:
            for y in (-14.0, 14.0):
                _segment(component, (0, y), (126, y), width=3.2)
            _taper(component, (25, 0), length=11, width1=1.2, width2=3.0)
            _segment(component, (36, 0), (57, 0), width=3.0)
            _bezier(component, (54, 0), dx=18, dy=7.0, width=2.6)
            _bezier(component, (54, 0), dx=18, dy=-7.0, width=2.6)
            _segment(component, (72, 7), (91, 7), width=3.0)
            _segment(component, (72, -7), (91, -7), width=3.0)
            _taper(component, (91, 7), length=10, width1=3.0, width2=1.2)
            _taper(component, (91, -7), length=10, width1=3.0, width2=1.2)
            return x_left, x_right, left, right
        rails = max(inputs, outputs, 2 + (variant == 1))
        outer = _spread(rails, pitch=22)
        inner = _spread(rails, pitch=8 if variant != 2 else 12)
        for index in range(rails):
            y0 = outer[index]
            yi = inner[index]
            width = 3.0 + (0.8 if variant == 1 and index == 1 else 0)
            _s_curve(component, (x_left, y0), dx=28, dy=yi - y0, width=width)
            _segment(component, (28, yi), (x_right - 28, yi), width=width)
            _s_curve(
                component,
                (x_right - 28, yi),
                dx=28,
                dy=outer[index] - yi,
                width=width,
            )
        if variant == 0:
            for x in (42, 63, 84):
                _rectangle(component, (x, 0), (5.0, 6.5))
        elif variant == 1:
            _taper(component, (34, 0), length=12, width1=1.2, width2=3.2)
            _taper(component, (80, 0), length=12, width1=3.2, width2=1.2)
        elif variant == 2:
            for index in range(9):
                angle = 214 + index * 13
                radians = math.radians(angle)
                _circle(
                    component,
                    (
                        63 + 20 * math.cos(radians),
                        19 + 20 * math.sin(radians),
                    ),
                    1.8 + 0.08 * index,
                )
        elif variant == 3:
            for x in range(46, 86, 7):
                _rectangle(component, (float(x), -3.8), (3.3, 3.0))
                _rectangle(component, (float(x), 3.8), (3.3, 3.0))
    return x_left, x_right, left, right


def _bus_loop_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
    *,
    hierarchical: bool,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 124.0 if hierarchical else 100.0
    left = _spread(inputs, pitch=22)
    right = _spread(outputs, pitch=22)
    buses = max(1, min(2, max(inputs, outputs)))
    bus_ys = _spread(buses, pitch=28)
    for y in bus_ys:
        _segment(component, (x_left, y), (x_right, y), width=3.4)
    if variant == 0:
        _ring(component, (x_right * 0.5, bus_ys[0] + 16), 12, width=3)
    elif variant == 1:
        _ring(component, (x_right * 0.42, 0), 12, width=3)
        _ring(component, (x_right * 0.67, 0), 9, width=3)
    elif variant == 2:
        _ring(component, (x_right * 0.46, 16), 15, width=3, angle=300, rotation=30)
        _bezier(component, (31, bus_ys[0]), dx=45, dy=0, width=3.4, hook=11)
    else:
        count = 4 if hierarchical else 2
        for index in range(count):
            _ring(component, (29 + index * 22, 14 if index % 2 == 0 else -14), 8, width=2.8)
    return x_left, x_right, left, right


def _crossing_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
    *,
    hierarchical: bool,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 112.0 if hierarchical else 90.0
    left = _spread(inputs, pitch=18)
    right = _spread(outputs, pitch=18)
    center = x_right / 2
    if not hierarchical and variant == 0 and inputs == 4 and outputs == 4:
        # Four independent routes with strictly increasing detour count.
        # Their vertical bands do not overlap, so the visual witness is a
        # delay bank rather than a crossing mesh.
        left = _spread(4, pitch=18)
        right = list(left)
        for route, y in enumerate(left):
            if route == 0:
                _segment(component, (0, y), (90, y), width=3.0)
                continue
            points: list[tuple[float, float]] = [(0, y)]
            step = 90 / (2 * route + 1)
            for index in range(1, 2 * route + 1):
                offset = 4.0 if index % 2 else -4.0
                points.append((index * step, y + offset))
            points.append((90, y))
            _polyline(component, points, width=3.0)
    elif variant == 0:
        _segment(component, (x_left, 0), (x_right, 0), width=3.6)
        _segment(component, (center, -34), (center, 34), width=3.6)
        _ellipse(component, (center, 0), (8 if hierarchical else 5, 8 if hierarchical else 5))
    elif variant == 1:
        _segment(component, (x_left, -18), (x_right, 18), width=3.6)
        _segment(component, (x_left, 18), (x_right, -18), width=3.6)
        if hierarchical:
            for rotation in (45, 225):
                _taper(
                    component,
                    (center - 9, 0),
                    length=18,
                    width1=3.6,
                    width2=8.0,
                    rotation=rotation,
                )
    elif variant == 2:
        _segment(component, (x_left, 0), (x_right, 0), width=3.6)
        _polyline(
            component,
            [(center - 28, -30), (center - 15, -12), (center + 15, -12), (center + 28, -30)],
            width=3.6,
        )
        _polyline(
            component,
            [(center - 28, 30), (center - 15, 12), (center + 15, 12), (center + 28, 30)],
            width=3.6,
        )
    else:
        axes = 3 if hierarchical else 2
        for index in range(axes):
            angle = index * 180 / axes
            radians = math.radians(angle)
            dx = math.cos(radians) * 52
            dy = math.sin(radians) * 36
            _segment(
                component,
                (center - dx, -dy),
                (center + dx, dy),
                width=3.2,
            )
        _ring(component, (center, 0), 9, width=3)
    # The review signature remains the executable contract even when a scene
    # includes extra internal routes not exposed as top-level terminals.
    return x_left, x_right, left, right


def _body_terminal_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
    *,
    fpr: bool,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 126.0 if fpr else 100.0
    body_left, body_right = (38.0, 86.0) if fpr else (31.0, 69.0)
    if variant == 2:
        # Exactly four visual terminals: west, north, east, and south.
        center_x = 50.0
        _rectangle(component, (center_x, 0), (30, 30))
        _segment(component, (0, 0), (35, 0), width=3.4)
        _segment(component, (65, 0), (100, 0), width=3.4)
        _segment(component, (center_x, 15), (center_x, 40), width=3.4)
        _segment(component, (center_x, -15), (center_x, -40), width=3.4)
        return x_left, x_right, [0.0, 40.0], [-40.0, 0.0]
    if variant == 4:
        # A thick open arc is a notched crescent body.  Each of its three
        # aperture rails overlaps the body material at its attachment.
        _ring(component, (52, 0), 23, width=12, angle=285, rotation=38)
        _taper(component, (0, 0), length=34, width1=3.4, width2=9.0)
        _bezier(component, (71, -18), dx=29, dy=11.5, width=3.2)
        _bezier(component, (51, 12), dx=31, dy=25, width=3.2, hook=8)
        return x_left, x_right, [0.0], [-6.5, 37.0]
    if variant == 5:
        # Two chamber rails per side, with no hidden duplicate bank.
        for y in (-11.0, 11.0):
            _ellipse(component, (50, y), (23, 10))
            _segment(component, (0, y), (29, y), width=3.4)
            _segment(component, (71, y), (100, y), width=3.4)
        _rectangle(component, (35, 0), (9, 8))
        _rectangle(component, (65, 0), (9, 8))
        return x_left, x_right, [-11.0, 11.0], [-11.0, 11.0]
    if variant == 6:
        # One input body forks into exactly two output bodies and terminals.
        _ellipse(component, (31, 0), (14, 19))
        _ellipse(component, (70, -14), (12, 14))
        _ellipse(component, (70, 14), (12, 14))
        _segment(component, (0, 0), (18, 0), width=3.4)
        for y in (-14.0, 14.0):
            _bezier(component, (43, 0), dx=17, dy=y, width=5.0)
            _segment(component, (80, y), (100, y), width=3.4)
        return x_left, x_right, [0.0], [-14.0, 14.0]
    if variant == 7:
        # A connected corridor surrounded by an irregular binary pixel field.
        _segment(component, (0, 0), (100, 0), width=4.0)
        occupied = {
            (0, 0),
            (1, 0),
            (2, 0),
            (2, 1),
            (3, -1),
            (3, 0),
            (4, -2),
            (4, 0),
            (4, 2),
            (5, -1),
            (5, 0),
            (5, 1),
            (6, -2),
            (6, 0),
            (7, 0),
            (7, 1),
            (8, 0),
        }
        for column, row in sorted(occupied):
            _rectangle(component, (28 + column * 5.2, row * 5.2), (4.4, 4.4))
        return x_left, x_right, [0.0], [0.0]
    if variant == 8:
        # An outlined chamber and island field with exactly three access leads.
        _segment(component, (0, 0), (26, 0), width=3.4)
        _segment(component, (74, -5), (100, -7), width=3.4)
        _segment(component, (74, 5), (100, 7), width=3.4)
        for x0, y0, x1, y1 in (
            (26, -16, 74, -16),
            (26, 16, 74, 16),
            (26, -16, 26, 16),
            (74, -16, 74, 16),
        ):
            _segment(component, (x0, y0), (x1, y1), width=3.0)
        for row in (-1, 0, 1):
            for column in range(6):
                if (row + column) % 3:
                    _ring(
                        component,
                        (35 + column * 6.2, row * 7.0),
                        2.1,
                        width=1.0,
                    )
        return x_left, x_right, [0.0], [-7.0, 7.0]
    body_ys = _spread(max(inputs, outputs, 2), pitch=8)
    left, right = _connect_terminal_banks(
        component,
        inputs=inputs,
        outputs=outputs,
        x_left=x_left,
        x_body_left=body_left,
        x_body_right=body_right,
        x_right=x_right,
        body_ys=body_ys,
        width=3.4,
    )
    if variant == 0:
        # One input and a visibly ranked three-aperture output bank.
        _ellipse(
            component,
            ((body_left + body_right) / 2, 0),
            ((body_right - body_left) / 2, 20),
        )
        for y in right:
            _taper(
                component,
                (body_right - 2, y * 0.45),
                length=15,
                width1=7.0,
                width2=3.4,
            )
    elif variant == 1:
        # A bilateral bank attached to the two long faces of one body.
        _rectangle(
            component,
            ((body_left + body_right) / 2, 0),
            (body_right - body_left, 33),
        )
        _ellipse(component, (body_left, 0), (9, 17))
        _ellipse(component, (body_right, 0), (9, 17))
    elif variant == 3:
        # Two separately legible bodies connected only by a narrow neck.
        _ellipse(component, (39, 0), (13, 18))
        _ellipse(component, (63, 0), (13, 18))
        _segment(component, (48, 0), (54, 0), width=5.0)
    else:
        raise ReleaseError(f"unsupported body-terminal proposal variant: {variant}")
    return x_left, x_right, left, right


def _repeated_media_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
    *,
    hierarchical: bool,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 128.0 if hierarchical else 100.0
    left = _spread(inputs, pitch=18)
    right = _spread(outputs, pitch=18)
    if not hierarchical and variant == 0:
        # Repetition is indexed along arc length, not along a straight ruler.
        path = gf.Path()
        path.append(gf.path.straight(18.0))
        path.append(gf.path.arc(radius=30.0, angle=112.0, npoints=120))
        path.append(gf.path.straight(22.0))
        component.add_ref(gf.path.extrude(path, cross_section=_xs(3.4)))
        indices = np.linspace(24, len(path.points) - 24, 9, dtype=int)
        for index, point_index in enumerate(indices):
            point = path.points[point_index]
            _rotated_rectangle(
                component,
                (float(point[0]), float(point[1]) + 4.0),
                (2.7, 6.0),
                -25.0 + index * 12.0,
            )
        end = path.points[-1]
        x_right = float(end[0])
        left, right = [0.0], [float(end[1])]
    elif not hierarchical and variant == 1:
        _segment(component, (0, 0), (100, 0), width=3.4)
        x = 20.0
        for _ in range(6):
            _rectangle(component, (x, 5.0), (2.6, 7.0))
            x += 4.0
            _rectangle(component, (x, 5.0), (4.0, 7.0))
            x += 7.0
    elif not hierarchical and variant == 2:
        _segment(component, (0, 0), (100, 0), width=3.4)
        for index in range(12):
            x = 20 + index * 6.0
            if index % 2:
                _rectangle(component, (x, 6.0), (3.2, 8.0))
            else:
                _circle(component, (x, 6.0), 3.0)
    elif not hierarchical and variant == 3:
        _segment(component, (0, 0), (36, 0), width=5.0)
        for index in range(9):
            x = 38 + index * 5.2
            width = 4.5 - index * 0.25
            _rectangle(component, (x, 0), (3.1, max(2.4, width)))
        _taper(component, (82, 0), length=18, width1=2.5, width2=3.4)
    else:
        rails = max(1, min(2, max(inputs, outputs)))
        rail_ys = _spread(rails, pitch=16)
        for y in rail_ys:
            _segment(component, (x_left, y), (x_right, y), width=3.4)
        if variant == 0:
            word = "ABAABABAABAAB"
            for index, symbol in enumerate(word):
                x = 22 + index * 7.2
                if symbol == "A":
                    _circle(component, (x, rail_ys[0] + 5.2), 2.6)
                else:
                    _rectangle(component, (x, rail_ys[0] + 5.2), (3.0, 7.0))
        elif variant == 1:
            for row, (y, pitch) in enumerate(zip((-7.0, 7.0), (5.0, 6.2), strict=True)):
                count = 15 if row == 0 else 12
                for index in range(count):
                    _circle(component, (23 + index * pitch, y), 1.8)
        elif variant == 2:
            for burst in range(5):
                origin = 22 + burst * 20
                for micro in range(3):
                    _rectangle(
                        component,
                        (origin + micro * 3.2, rail_ys[0] + 5),
                        (2.0, 6.0),
                    )
        elif variant == 3:
            for index in range(7):
                _rectangle(component, (19 + index * 5.0, rail_ys[0]), (2.8, 5.0))
                _rectangle(component, (94 + index * 5.0, rail_ys[0]), (2.8, 5.0))
            _segment(component, (55, rail_ys[0]), (91, rail_ys[0]), width=6.0)
    return x_left, x_right, left, right


def _interferometer_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
    *,
    final_component: bool,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 145.0 if final_component else 128.0
    left = _spread(inputs, pitch=12)
    right = _spread(outputs, pitch=12)
    stages = 2 if variant in {2, 3} else 1
    stage_width = (x_right - 28) / stages
    for y in left:
        _segment(component, (x_left, y), (14, y), width=3.3)
    x = 14.0
    for stage in range(stages):
        split = x + 7
        join = x + stage_width - 7
        _ellipse(component, (split, 0), (6, 11))
        _ellipse(component, (join, 0), (6, 11))
        arm_offsets = (-13, 13) if variant != 1 else (-19, 8)
        for arm_index, arm_y in enumerate(arm_offsets):
            extra = 10 if variant == 0 and arm_index == 0 else 0
            _polyline(
                component,
                [
                    (split + 4, 0),
                    (split + 15, arm_y),
                    ((split + join) / 2, arm_y + extra),
                    (join - 15, arm_y),
                    (join - 4, 0),
                ],
                width=3.1,
            )
        if variant == 3:
            _ring(component, ((split + join) / 2, arm_offsets[0] - 10), 7, width=2.6)
        x += stage_width
    for y in right:
        _bezier(component, (x_right - 16, 0), dx=16, dy=y, width=3.3)
    return x_left, x_right, left, right


def _fpr_bank_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
    *,
    awg: bool,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 172.0 if awg else 138.0
    left = _spread(inputs, pitch=10)
    right = _spread(outputs, pitch=10)
    first_x = 40.0
    second_x = 130.0 if awg else 98.0
    _ellipse(component, (first_x, 0), (20, 27))
    _ellipse(component, (second_x, 0), (20, 27))
    for y in left:
        _bezier(component, (x_left, y), dx=first_x - 18, dy=-y, width=3.2)
    for y in right:
        _bezier(component, (second_x + 18, 0), dx=x_right - second_x - 18, dy=y, width=3.2)
    arm_count = 5 + variant + (1 if awg else 0)
    for index, y in enumerate(_spread(arm_count, pitch=7.0)):
        rank = abs(index - (arm_count - 1) / 2)
        lift = 30 + rank * (5.0 + 0.8 * variant)
        if variant == 3:
            lift *= -1 if index % 2 else 1
        _polyline(
            component,
            [
                (first_x + 17, y * 0.38),
                (first_x + 28, y),
                ((first_x + second_x) / 2, y + lift),
                (second_x - 28, y),
                (second_x - 17, y * 0.38),
            ],
            width=2.4,
        )
    if awg and variant in {2, 3}:
        for index in range(7):
            _rectangle(
                component,
                (first_x - 1 + index * 5, -27 + (index % 2) * 3),
                (2.2, 7 + index * 0.7),
            )
    return x_left, x_right, left, right


def _mode_evolution_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
    *,
    final_component: bool,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 132.0 if final_component else 112.0
    left = _spread(inputs, pitch=13)
    right = _spread(outputs, pitch=13)
    rail_count = max(inputs, outputs, 2 + (variant == 2))
    starts = _spread(rail_count, pitch=17)
    ends = list(reversed(_spread(rail_count, pitch=8 + 2 * (variant == 3))))
    for index, (y0, y1) in enumerate(zip(starts, ends, strict=True)):
        width1 = 2.7 + index * 0.45
        width2 = 5.2 - index * 0.35
        _bezier(component, (x_left, y0), dx=x_right, dy=y1 - y0, width=(width1 + width2) / 2)
        for zone in range(4):
            x = 24 + zone * 24
            width = width1 + (width2 - width1) * zone / 3
            _rectangle(component, (x, y0 + (y1 - y0) * x / x_right), (12, width + 1.3))
    if variant == 1:
        _teeth(component, x0=43, y=0, count=8, pitch=6, width=2.2, bilateral=True)
    if variant == 3:
        _ring(component, (x_right / 2, 0), 9, width=2.5, angle=260, rotation=50)
    return x_left, x_right, left, right


def _l3_mux_hierarchy(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 132.0
    left = _spread(inputs, pitch=18)
    right = _spread(outputs, pitch=16)
    if variant == 0:
        # One asymmetric body with five contacts distributed over three edges.
        _ellipse(component, (65, 0), (26, 31))
        for y in left:
            _bezier(component, (0, y), dx=43, dy=-0.45 * y, width=3.2)
        for y in right[:2]:
            _bezier(component, (87, 0.35 * y), dx=45, dy=0.65 * y, width=3.2)
        _segment(component, (65, 31), (65, 46), width=3.2)
    elif variant == 1:
        # A first body emits one direct route and one route into a secondary
        # 1x2 body, so the hierarchy has 2 inputs and 3 outputs.
        _ellipse(component, (36, 0), (18, 24))
        _rectangle(component, (91, 10), (30, 28))
        for y in left:
            _bezier(component, (0, y), dx=22, dy=-y, width=3.2)
        _polyline(component, [(53, -6), (75, -14), (132, right[0])], width=3.0)
        _polyline(component, [(53, 6), (71, 10), (76, 10)], width=3.0)
        for target in right[1:]:
            _bezier(component, (106, 10), dx=26, dy=target - 10, width=3.0)
    elif variant == 2:
        # A Y root feeds unlike second-stage nodes: one compact body and one
        # explicit path fork.  This is the hybrid-node witness.
        _segment(component, (0, 0), (24, 0), width=3.5)
        _ellipse(component, (31, 0), (8, 11))
        for sign in (-1, 1):
            _bezier(component, (37, 0), dx=28, dy=sign * 16, width=3.1)
        _ellipse(component, (72, -16), (7, 10))
        for target in right[:2]:
            _bezier(component, (79, -16), dx=53, dy=target + 16, width=3.0)
        _segment(component, (65, 16), (81, 16), width=3.0)
        for target in right[2:]:
            _bezier(component, (81, 16), dx=51, dy=target - 16, width=3.0)
    elif variant == 3:
        # Two inputs fan into three routes and reconverge into two outputs.
        for y in left:
            _bezier(component, (0, y), dx=29, dy=-y, width=3.2)
        _ellipse(component, (36, 0), (8, 14))
        _ellipse(component, (96, 0), (8, 14))
        for index, y in enumerate((-17.0, 0.0, 17.0)):
            lift = 7.0 if index == 1 else 0.0
            _polyline(
                component,
                [(42, 0), (55, y), (72, y + lift), (90, y), (90, 0)],
                width=3.0,
            )
        for y in right:
            _bezier(component, (102, 0), dx=30, dy=y, width=3.2)
    else:
        raise ReleaseError(f"unsupported L3 hierarchy proposal variant: {variant}")
    return x_left, x_right, left, right


def _l3_interferometer_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 142.0
    left = _spread(inputs, pitch=14)
    right = _spread(outputs, pitch=14)
    if variant == 0:
        # Two rails form linked cycles around one explicit arm-exchange bridge.
        _ellipse(component, (25, 0), (7, 13))
        _ellipse(component, (117, 0), (7, 13))
        _polyline(component, [(31, 0), (46, -18), (67, -18), (82, 18), (103, 18), (111, 0)], width=3.0)
        _polyline(component, [(31, 0), (46, 18), (67, 18), (82, -18), (103, -18), (111, 0)], width=3.0)
        _ellipse(component, (74.5, 0), (7, 10))
    elif variant == 1:
        # Two full stages share the center coupling node.
        for center in (36.0, 104.0):
            _ellipse(component, (center - 18, 0), (6, 11))
            _ellipse(component, (center + 18, 0), (6, 11))
            for y in (-14.0, 14.0):
                _polyline(
                    component,
                    [(center - 13, 0), (center - 6, y), (center + 6, y), (center + 13, 0)],
                    width=3.0,
                )
        _segment(component, (60, 0), (80, 0), width=3.2)
    elif variant == 2:
        _ellipse(component, (27, 0), (7, 12))
        _ellipse(component, (113, 0), (7, 12))
        for y in (-16.0, 16.0):
            _polyline(component, [(33, 0), (47, y), (99, y), (107, 0)], width=3.1)
        _ellipse(component, (72, -27), (11, 8))
        _segment(component, (61, -16), (61, -23), width=2.7)
        _segment(component, (83, -23), (83, -16), width=2.7)
        _segment(component, (18, 0), (21, 0), width=3.2)
        _segment(component, (119, 0), (123, 0), width=3.2)
    elif variant == 3:
        _ellipse(component, (29, 0), (7, 12))
        _ellipse(component, (100, 0), (7, 12))
        _polyline(component, [(35, 0), (49, -15), (88, -15), (94, 0)], width=3.0)
        _polyline(component, [(35, 0), (49, 15), (78, 15)], width=3.0)
        _ring(component, (94, 15), 16, width=3.0, angle=300, rotation=30)
        _polyline(component, [(110, 15), (118, 15), (106, 0)], width=3.0)
        _segment(component, (18, 0), (23, 0), width=3.2)
        _segment(component, (105, 0), (123, 0), width=3.2)
    else:
        raise ReleaseError(f"unsupported L3 interferometer variant: {variant}")
    for y in left:
        _bezier(component, (0, y), dx=18, dy=-y, width=3.2)
    for y in right:
        _bezier(component, (123, 0), dx=19, dy=y, width=3.2)
    return x_left, x_right, left, right


def _l3_resonator_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 132.0
    left = _spread(inputs, pitch=24)
    right = _spread(outputs, pitch=24)
    if variant == 0:
        _segment(component, (0, -12), (132, -12), width=3.2)
        for x in (42, 66, 90):
            _ring(component, (x, 2), 10, width=2.8)
        left, right = [-12.0], [-12.0]
    elif variant == 1:
        _segment(component, (0, 0), (30, 0), width=3.2)
        _polyline(
            component,
            [(30, 0), (40, 18), (57, 18), (66, 0), (57, -18), (40, -18), (30, 0)],
            width=3.0,
        )
        _polyline(
            component,
            [(66, 0), (75, 18), (92, 18), (102, 0), (92, -18), (75, -18), (66, 0)],
            width=3.0,
        )
        _segment(component, (102, 0), (132, 0), width=3.2)
        left, right = [0.0], [0.0]
    elif variant == 2:
        for y in (-15.0, 15.0):
            _segment(component, (0, y), (132, y), width=3.2)
        _ring(component, (55, 0), 11, width=2.7)
        _ring(component, (79, 0), 14, width=2.7)
    elif variant == 3:
        _segment(component, (0, -12), (132, -12), width=3.0)
        for center in ((55, -3), (79, -3), (67, 18)):
            _ring(component, center, 9, width=2.5)
        left, right = [-12.0], [-12.0]
    else:
        raise ReleaseError(f"unsupported L3 resonator variant: {variant}")
    return x_left, x_right, left, right


def _lattice_cells(
    component: gf.Component,
    *,
    columns: int,
    rows: int,
    origin: tuple[float, float],
    pitch_x: float,
    pitch_y: float,
    omitted: Callable[[int, int], bool],
    shifted: Mapping[tuple[int, int], tuple[float, float]] | None = None,
    radius: float = 1.7,
    void: bool = False,
) -> None:
    """Draw a primitive-cell lattice with an explicit vacancy/shift rule."""

    x0, y0 = origin
    offsets = shifted or {}
    for column in range(columns):
        for row in range(rows):
            if omitted(column, row):
                continue
            dx, dy = offsets.get((column, row), (0.0, 0.0))
            center = (
                x0 + column * pitch_x + dx,
                y0 + (row - (rows - 1) / 2) * pitch_y + dy,
            )
            if void:
                _void_circle(component, center, radius)
            else:
                _circle(component, center, radius)


def _l3_lattice_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 112.0
    left = _spread(inputs, pitch=18)
    right = _spread(outputs, pitch=18)
    if variant == 0:
        # Two vacancy channels approach, share a finite parallel coupling
        # window, then depart without becoming a generic crossing.
        def omitted(column: int, row: int) -> bool:
            if column < 4 or column > 8:
                return row in {2, 6}
            return row in {3, 5}

        _rectangle(component, (56, 0), (68, 50))
        _lattice_cells(
            component,
            columns=13,
            rows=9,
            origin=(25, 0),
            pitch_x=5.2,
            pitch_y=5.2,
            omitted=omitted,
            void=True,
        )
        for y in (-10.4, 10.4):
            _segment(component, (0, y), (23, y), width=3.0)
            _segment(component, (89, y), (112, y), width=3.0)
        left, right = [-10.4, 10.4], [-10.4, 10.4]
    elif variant == 1:
        # One incoming vacancy splits into upper and lower exits.
        def omitted(column: int, row: int) -> bool:
            if column <= 6:
                return row == 5
            delta = column - 6
            return row in {max(1, 5 - delta // 2), min(9, 5 + delta // 2)}

        _rectangle(component, (56, 0), (68, 56))
        _lattice_cells(
            component,
            columns=13,
            rows=11,
            origin=(25, 0),
            pitch_x=5.2,
            pitch_y=4.8,
            omitted=omitted,
            void=True,
        )
        _segment(component, (0, 0), (23, 0), width=3.0)
        _segment(component, (89, -15), (112, -15), width=3.0)
        _segment(component, (89, 15), (112, 15), width=3.0)
        left, right = [0.0], [-15.0, 15.0]
    elif variant == 2:
        # Two cell pitches meet at one vertical heterostructure wall.
        _rectangle(component, (58, 0), (80, 58))
        _lattice_cells(
            component,
            columns=7,
            rows=11,
            origin=(22, 0),
            pitch_x=4.6,
            pitch_y=4.6,
            omitted=lambda column, row: row == 5,
            radius=1.55,
            void=True,
        )
        _lattice_cells(
            component,
            columns=7,
            rows=9,
            origin=(59, 0),
            pitch_x=6.0,
            pitch_y=5.6,
            omitted=lambda column, row: row == 4,
            radius=1.9,
            void=True,
        )
        _segment(component, (0, 0), (20, 0), width=3.0)
        _segment(component, (95, 0), (112, 0), width=3.0)
    elif variant == 3:
        shifts = {
            (5, 3): (-1.5, -1.0),
            (6, 3): (1.5, -1.0),
            (5, 4): (-1.5, 1.0),
            (6, 4): (1.5, 1.0),
            (5, 5): (-1.0, 1.5),
            (6, 5): (1.0, 1.5),
        }
        _rectangle(component, (56, 0), (68, 50))
        _lattice_cells(
            component,
            columns=13,
            rows=9,
            origin=(25, 0),
            pitch_x=5.2,
            pitch_y=5.2,
            omitted=lambda column, row: row == 4,
            shifted=shifts,
            void=True,
        )
        _segment(component, (0, 0), (23, 0), width=3.0)
        _segment(component, (89, 0), (112, 0), width=3.0)
    else:
        raise ReleaseError(f"unsupported L3 lattice proposal variant: {variant}")
    return x_left, x_right, left, right


def _strip_slot_swg_scene(
    component: gf.Component,
    *,
    x_left: float,
    x_right: float,
    y: float = 0.0,
) -> None:
    """Draw one legible strip → slot → SWG → strip grammar."""

    _segment(component, (x_left, y), (22, y), width=5.0)
    for sign in (-1, 1):
        _bezier(component, (22, y), dx=18, dy=sign * 4.2, width=2.6)
        _segment(component, (40, y + sign * 4.2), (67, y + sign * 4.2), width=2.6)
    for index in range(7):
        x = 70 + index * 5.0
        height = 8.0 - index * 0.45
        _rectangle(component, (x, y), (3.1, height))
    _taper(component, (102, y), length=x_right - 102, width1=4.5, width2=3.2)


def _l3_mode_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 132.0
    left = _spread(inputs, pitch=16)
    right = _spread(outputs, pitch=16)
    if variant == 0:
        _strip_slot_swg_scene(component, x_left=0, x_right=132)
    elif variant == 1:
        _segment(component, (0, 0), (20, 0), width=7.0)
        _taper(component, (20, 0), length=72, width1=7.0, width2=1.8)
        for index in range(10):
            x = 34 + index * 5.3
            height = 12 - index * 0.7
            _rectangle(component, (x, 5 + height / 2), (2.5, height))
            _rectangle(component, (x, -5 - height / 2), (2.5, height))
        _taper(component, (92, 0), length=40, width1=1.8, width2=3.2)
    elif variant == 2:
        for y, width in zip(left, (3.0, 5.0), strict=True):
            _bezier(component, (0, y), dx=45, dy=-0.6 * y, width=width)
        _taper(component, (45, 0), length=18, width1=1.2, width2=4.0)
        _segment(component, (63, 0), (88, 0), width=8.0)
        _taper(component, (88, 0), length=44, width1=8.0, width2=3.2)
    elif variant == 3:
        # Four tips merge pairwise and then through one second-level node.
        pair_centers = (-10.0, 10.0)
        for index, y in enumerate(left):
            pair = index // 2
            _bezier(
                component,
                (0, y),
                dx=38,
                dy=pair_centers[pair] - y,
                width=2.8,
            )
        for y in pair_centers:
            _taper(component, (38, y), length=20, width1=3.0, width2=6.0)
            _bezier(component, (58, y), dx=28, dy=-y, width=5.0)
        _taper(component, (86, 0), length=46, width1=9.0, width2=3.2)
    else:
        raise ReleaseError(f"unsupported L3 mode proposal variant: {variant}")
    return x_left, x_right, left, right


def _l3_fpr_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 164.0
    left = _spread(inputs, pitch=14)
    right = _spread(outputs, pitch=12)
    if variant == 0:
        _ellipse(component, (38, 0), (19, 26))
        _ellipse(component, (126, 0), (19, 26))
        for y in left:
            _bezier(component, (0, y), dx=20, dy=-y, width=3.0)
        for y in right:
            _bezier(component, (144, 0), dx=20, dy=y, width=3.0)
        for index, y in enumerate(_spread(6, pitch=6.2)):
            lift = 29 + abs(index - 2.5) * 7
            _polyline(component, [(55, 0.45 * y), (68, y), (82, y + lift), (109, y), (109, 0.45 * y)], width=2.5)
    elif variant == 1:
        # A single free-propagation slab faces an unmistakable *discrete*
        # concave reflector bank.  A reflective FPR returns to a shared-side
        # aperture bank; no rail is allowed to pass through the facet bank.
        _ellipse(component, (59, 0), (25, 34))
        left = [-28.0]
        right = [-14.0, 0.0, 14.0, 28.0]
        for y in left + right:
            _bezier(
                component,
                (0, y),
                dx=46,
                dy=-0.45 * y,
                width=3.0,
                hook=-0.18 * y,
            )
        facet_ys = _spread(11, pitch=6.0)
        for y in facet_ys:
            x = 111.0 + (y / 15.0) ** 2
            tangent_degrees = math.degrees(math.atan2(1.0, 2.0 * y / 225.0))
            _rotated_rectangle(
                component,
                (x, y),
                (3.2, 5.0),
                tangent_degrees,
            )
        x_right = 0.0
    elif variant == 2:
        _ring(component, (82, 0), 29, width=13, angle=310, rotation=25)
        _bezier(component, (0, -9), dx=56, dy=2, width=3.0)
        _segment(component, (0, 42), (28, 42), width=3.0)
        _bezier(component, (28, 42), dx=48, dy=-17, width=3.0, hook=-8)
        # Start inside the annular envelope so the upper-right tangential
        # aperture is a real body contact rather than a floating rail.
        _bezier(component, (98, 8), dx=66, dy=1, width=3.0)
        _bezier(component, (88, -27), dx=48, dy=-15, width=3.0, hook=8)
        _segment(component, (136, -42), (164, -42), width=3.0)
        left, right = [-9.0, 42.0], [-42.0, 9.0]
    elif variant == 3:
        _ellipse(component, (39, 0), (18, 25))
        _ellipse(component, (125, 0), (18, 25))
        for y in left:
            _bezier(component, (0, y), dx=22, dy=-y, width=3.0)
        for y in right:
            _bezier(component, (142, 0), dx=22, dy=y, width=3.0)
        for index, y in enumerate(_spread(6, pitch=6.2)):
            depth = 27 + abs(index - 2.5) * 6
            _polyline(
                component,
                [(55, y * 0.4), (70, y), (70, y + depth), (106, y + depth), (106, y), (109, y * 0.4)],
                width=2.5,
            )
    else:
        raise ReleaseError(f"unsupported L3 FPR proposal variant: {variant}")
    return x_left, x_right, left, right


def _l4_awg_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 204.0
    left = _spread(inputs, pitch=14)
    right = _spread(outputs, pitch=12)
    if variant == 0:
        # Three slabs and two oppositely ranked banks make the second stage
        # visible; this cannot collapse to the L3 dual-slab precursor.
        for x in (37.0, 102.0, 167.0):
            _ellipse(component, (x, 0), (17, 25))
        for y in left:
            _bezier(component, (0, y), dx=21, dy=-y, width=3.1)
        for y in right:
            _bezier(component, (183, 0), dx=21, dy=y, width=3.1)
        for bank, (start, stop, direction) in enumerate(
            ((53.0, 85.0, 1.0), (119.0, 151.0, -1.0))
        ):
            del bank
            for index, y in enumerate(_spread(5, pitch=5.0)):
                lift = direction * (20 + abs(index - 2) * 6)
                _polyline(
                    component,
                    [(start, 0.4 * y), (start + 8, y), ((start + stop) / 2, y + lift), (stop - 8, y), (stop, 0.4 * y)],
                    width=2.4,
                )
    elif variant == 1:
        # One input slab fans into two intermediate slabs; each owns a ranked
        # bank and two output channels.
        _ellipse(component, (39, 0), (19, 27))
        for center in ((102, -24), (102, 24)):
            _ellipse(component, center, (16, 21))
        for y in left:
            _bezier(component, (0, y), dx=21, dy=-y, width=3.1)
        for sign in (-1, 1):
            for index, y in enumerate(_spread(4, pitch=4.5)):
                target_y = sign * 24 + y
                lift = sign * (17 + index * 4)
                _polyline(
                    component,
                    [(56, sign * 5), (68, sign * 15), (82, target_y + lift), (86, target_y), (87, target_y * 0.45)],
                    width=2.4,
                )
        for group, center_y in enumerate((-24.0, 24.0)):
            for target in right[group * 2 : group * 2 + 2]:
                _bezier(component, (118, center_y), dx=86, dy=target - center_y, width=2.8)
    elif variant == 2:
        # A visible path permutation links the two FPRs.
        _ellipse(component, (43, 0), (20, 28))
        _ellipse(component, (161, 0), (20, 28))
        for y in left:
            _bezier(component, (0, y), dx=25, dy=-y, width=3.1)
        for y in right:
            _bezier(component, (179, 0), dx=25, dy=y, width=3.1)
        starts = _spread(4, pitch=9.0)
        permutation = (2, 0, 3, 1)
        stops = [starts[index] for index in permutation]
        for index, (y0, y1) in enumerate(zip(starts, stops, strict=True)):
            detour = (-28.0, 22.0, -18.0, 31.0)[index]
            _polyline(
                component,
                [(60, 0.4 * y0), (76, y0), (102, detour), (128, y1), (144, 0.4 * y1)],
                width=2.5,
            )
    elif variant == 3:
        # Two orthogonal propagation bodies exchange through one resolved
        # central aperture instead of merely adding ports to one square slab.
        _ellipse(component, (81, 0), (29, 20))
        _ellipse(component, (123, 0), (20, 29))
        _ellipse(component, (102, 0), (10, 10))
        _segment(component, (0, 0), (52, 0), width=3.1)
        _segment(component, (143, 0), (204, 0), width=3.1)
        _segment(component, (123, 27), (123, 48), width=3.0)
        _segment(component, (123, -27), (123, -48), width=3.0)
        left, right = [0.0, 48.0], [-48.0, 0.0]
    elif variant == 4:
        # A single slab fans into ranked arms, each ending in a loop mirror;
        # the four forward outputs leave from the same slab.
        _ellipse(component, (48, 0), (23, 30))
        for y in left:
            _bezier(component, (0, y), dx=26, dy=-y, width=3.1)
        for y in right:
            _bezier(component, (69, 0.45 * y), dx=135, dy=0.55 * y, width=2.8)
        for index, y in enumerate(_spread(6, pitch=7.0)):
            x_end = 101 + index * 8
            lift = 30 + abs(index - 2.5) * 5
            _polyline(
                component,
                [(68, 0.4 * y), (82, y), (90, y + lift), (x_end, y + lift)],
                width=2.4,
            )
            _ring(
                component,
                (x_end + 7, y + lift),
                7,
                width=2.3,
                angle=300,
                rotation=30,
            )
    elif variant == 5:
        # Two delay orders are interleaved above and below the slab axis.
        _ellipse(component, (43, 0), (20, 28))
        _ellipse(component, (161, 0), (20, 28))
        for y in left:
            _bezier(component, (0, y), dx=25, dy=-y, width=3.1)
        for y in right:
            _bezier(component, (179, 0), dx=25, dy=y, width=3.1)
        for index, y in enumerate(_spread(8, pitch=4.8)):
            family = index % 2
            direction = 1 if family == 0 else -1
            lift = direction * (30 + (index // 2) * (6 if family == 0 else 10))
            _polyline(
                component,
                [(60, 0.4 * y), (75, y), (102, y + lift), (144, y), (144, 0.4 * y)],
                width=2.3,
            )
    else:
        raise ReleaseError(f"unsupported L4 AWG proposal variant: {variant}")
    return x_left, x_right, left, right


def _l4_multiport_repeated_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 150.0
    left = _spread(inputs, pitch=18)
    right = _spread(outputs, pitch=18)
    if variant == 0:
        # Two segmented rails chirp in opposite directions through one
        # directional-coupling window.
        for y in (-8.0, 8.0):
            _segment(component, (0, y), (26, y), width=3.0)
            _segment(component, (124, y), (150, y), width=3.0)
        for row, y in enumerate((-4.0, 4.0)):
            x = 31.0
            for index in range(12):
                width = 2.4 + (index if row == 0 else 11 - index) * 0.11
                pitch = 4.0 + index * 0.16
                _rectangle(component, (x, y), (width, 3.2))
                x += pitch
            _s_curve(component, (18, (-8.0, 8.0)[row]), dx=13, dy=y - (-8.0, 8.0)[row], width=3.0)
            _s_curve(component, (x, y), dx=124 - x, dy=(-8.0, 8.0)[row] - y, width=3.0)
    elif variant == 1:
        for y in (-12.0, 12.0):
            _segment(component, (0, y), (150, y), width=3.0)
        for row, y in enumerate((-7.0, 7.0)):
            for index in range(9):
                x = 39 + index * 8.0
                if row == 1 and index == 4:
                    continue
                _rectangle(component, (x, y), (3.0, 6.0))
        _ring(component, (71, 0), 4.5, width=1.6)
    elif variant == 2:
        # Three periodic input rails interact in two windows before merging.
        inner = (-8.0, 0.0, 8.0)
        for y0, yi in zip(left, inner, strict=True):
            _bezier(component, (0, y0), dx=30, dy=yi - y0, width=2.8)
        for row, y in enumerate(inner):
            for zone_x in (38.0, 76.0):
                for index in range(5):
                    _rectangle(component, (zone_x + index * 5.0, y), (3.0, 3.0 + row))
        for y in inner:
            _bezier(component, (101, y), dx=31, dy=-y, width=3.1)
        _taper(component, (132, 0), length=18, width1=8.0, width2=3.2)
    elif variant == 3:
        # One solid input becomes a trident whose arms instantiate uniform,
        # dimerized, and chirped segmented media.
        _segment(component, (0, 0), (30, 0), width=3.2)
        branch_ys = (-16.0, 0.0, 16.0)
        for y in branch_ys:
            _bezier(component, (30, 0), dx=28, dy=y, width=3.0)
        for index in range(12):
            _rectangle(component, (62 + index * 5.0, -16), (3.0, 3.4))
        x = 62.0
        for index in range(10):
            _rectangle(component, (x, 0), ((2.5, 3.7)[index % 2], 3.4))
            x += (4.2, 6.2)[index % 2]
        x = 62.0
        for index in range(10):
            width = 2.4 + index * 0.13
            _rectangle(component, (x, 16), (width, 3.4))
            x += 4.0 + index * 0.22
        for y in branch_ys:
            _segment(component, (112, y), (150, y), width=3.0)
        left, right = [0.0], list(branch_ys)
    else:
        raise ReleaseError(f"unsupported L4 repeated proposal variant: {variant}")
    return x_left, x_right, left, right


def _l4_mode_mux_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 150.0
    left = _spread(inputs, pitch=13)
    right = _spread(outputs, pitch=13)
    if variant == 0:
        _rectangle(component, (75, 0), (58, 34))
        for y in left:
            _taper(component, (0, y), length=46, width1=3.0, width2=7.0)
        for y in right:
            _taper(component, (104, y), length=46, width1=7.0, width2=3.0)
        for y in (-10.0, 0.0, 10.0):
            _segment(component, (52, y), (98, -y), width=2.4)
    elif variant == 1:
        for y, width in zip(left, (3.0, 5.5), strict=True):
            _bezier(component, (0, y), dx=50, dy=-0.55 * y, width=width)
        _segment(component, (50, -4.0), (87, -4.0), width=3.0)
        _segment(component, (50, 4.0), (78, 4.0), width=5.5)
        _taper(component, (78, 4.0), length=13, width1=5.5, width2=1.2)
        _taper(component, (87, -4.0), length=63, width1=8.0, width2=3.2)
    elif variant == 2:
        # All four rails continuously shrink pitch and widen together; there
        # are no pairwise tree nodes as in the L3 merge hierarchy.
        target_pitch = 3.2
        for index, y0 in enumerate(left):
            y1 = _spread(4, pitch=target_pitch)[index]
            _bezier(component, (0, y0), dx=102, dy=y1 - y0, width=2.8 + index * 0.25)
            for zone in range(4):
                x = 30 + zone * 22
                y = y0 + (y1 - y0) * x / 102
                _rectangle(component, (x, y), (10, 3.0 + zone * 0.6))
        _taper(component, (102, 0), length=48, width1=13.0, width2=3.2)
    elif variant == 3:
        # Wide strip -> slot pair -> center-rail nucleation -> three outputs.
        _segment(component, (0, 0), (24, 0), width=7.0)
        for sign in (-1, 1):
            _bezier(component, (24, 0), dx=24, dy=sign * 5.0, width=3.0)
            _segment(component, (48, sign * 5.0), (82, sign * 5.0), width=3.0)
        _taper(component, (56, 0), length=14, width1=1.2, width2=3.2)
        _segment(component, (70, 0), (82, 0), width=3.2)
        for y, target in zip((-5.0, 0.0, 5.0), right, strict=True):
            _bezier(component, (82, y), dx=68, dy=target - y, width=3.0)
    else:
        raise ReleaseError(f"unsupported L4 mode-mux variant: {variant}")
    return x_left, x_right, left, right


def _resonant_filter_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 146.0
    left = _spread(inputs, pitch=25)
    right = _spread(outputs, pitch=25)
    if variant <= 3:
        for y in _spread(max(1, min(2, max(inputs, outputs))), pitch=25):
            _segment(component, (x_left, y), (x_right, y), width=3.2)
    if variant == 0:  # Dual-bus staggered four-ring CROW ladder.
        for index, x in enumerate((42, 63, 84, 105)):
            _ring(component, (x, -2 if index % 2 else 2), 9, width=2.7)
    elif variant == 1:  # Sequential unequal-radius Vernier pair.
        _ring(component, (57, 1), 11, width=2.8)
        _ring(component, (92, 1), 15, width=2.8)
    elif variant == 2:  # Unequal counter-arm ring loads on a complete MZI.
        _ellipse(component, (29, 0), (7, 12))
        _ellipse(component, (116, 0), (7, 12))
        for y in (-17.0, 17.0):
            _polyline(component, [(35, 0), (49, y), (102, y), (110, 0)], width=3.0)
        _ring(component, (67, 29), 9, width=2.6)
        _ring(component, (88, -30), 11, width=2.6)
    elif variant == 3:  # Four-ring square plaquette between opposing buses.
        for center in ((59, -8), (87, -8), (59, 20), (87, 20)):
            _ring(component, center, 9, width=2.5)
    elif variant == 4:  # Fin-loaded tapered distributed Bragg reflector.
        _segment(component, (0, 0), (18, 0), width=4.0)
        _taper(component, (18, 0), length=42, width1=4.0, width2=7.0)
        _segment(component, (60, 0), (86, 0), width=7.0)
        _taper(component, (86, 0), length=42, width1=7.0, width2=4.0)
        _segment(component, (128, 0), (146, 0), width=4.0)
        for bank, start in enumerate((26.0, 94.0)):
            for index in range(8):
                x = start + index * 4.0
                rank = index if bank == 0 else 7 - index
                height = 5.0 + rank * 0.75
                _rectangle(component, (x, 4 + height / 2), (2.0, height))
                _rectangle(component, (x, -4 - height / 2), (2.0, height))
        _ring(component, (73, 0), 5.0, width=1.6)
        left, right = [0.0], [0.0]
    elif variant == 5:  # AB|BA domain-wall Bragg cavity.
        _segment(component, (0, 0), (146, 0), width=3.2)
        x_positions = [25, 29, 36, 40, 47, 51, 58, 62, 69, 73]
        x_positions += [82, 89, 93, 100, 104, 111, 115, 122, 126, 133]
        for index, x in enumerate(x_positions):
            height = 8.5 if index % 2 else 6.0
            _rectangle(component, (x, 5 + height / 2), (2.5, height))
            _rectangle(component, (x, -5 - height / 2), (2.5, height))
        left, right = [0.0], [0.0]
    else:
        raise ReleaseError(f"unsupported L4 filter proposal variant: {variant}")
    return x_left, x_right, left, right


def _l4_interferometer_loop(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 156.0
    left = _spread(inputs, pitch=14)
    right = _spread(outputs, pitch=14)
    if variant == 0:
        # A visible two-rail coupling window closes into one feedback loop.
        _segment(component, (0, 0), (18, 0), width=3.2)
        _ellipse(component, (24, 0), (6, 10))
        for y in (-5.0, 5.0):
            _bezier(component, (29, 0), dx=12, dy=y, width=3.0)
        _polyline(
            component,
            [(41, -5), (58, -5), (75, -27), (118, -27), (135, 0)],
            width=3.0,
        )
        _polyline(
            component,
            [(41, 5), (58, 5), (75, 27), (118, 27), (135, 0)],
            width=3.0,
        )
        _segment(component, (135, 0), (156, 0), width=3.2)
        left, right = [0.0], [0.0]
    elif variant == 1:
        # Unequal Michelson arms terminate in circular loop reflectors.
        _segment(component, (0, 0), (30, 0), width=3.2)
        _ellipse(component, (37, 0), (7, 12))
        _polyline(component, [(43, 0), (58, -17), (103, -17)], width=3.0)
        _polyline(component, [(43, 0), (58, 17), (121, 17)], width=3.0)
        _ring(component, (112, -17), 9, width=2.7, angle=300, rotation=30)
        _ring(component, (130, 17), 9, width=2.7, angle=300, rotation=30)
        _polyline(component, [(103, -17), (78, -3), (52, 0)], width=2.8)
        _polyline(component, [(121, 17), (88, 4), (52, 0)], width=2.8)
        _segment(component, (52, 0), (156, 0), width=2.6)
        left, right = [0.0], [0.0]
    elif variant == 2:
        # Three directional coupling windows delimit two interferometer cells.
        rail_ys = (-8.0, 8.0)
        for y in rail_ys:
            _segment(component, (0, y), (156, y), width=3.0)
        for center in (31.0, 78.0, 125.0):
            _s_curve(component, (center - 11, -8), dx=11, dy=4.5, width=3.0)
            _s_curve(component, (center, -3.5), dx=11, dy=-4.5, width=3.0)
            _s_curve(component, (center - 11, 8), dx=11, dy=-4.5, width=3.0)
            _s_curve(component, (center, 3.5), dx=11, dy=4.5, width=3.0)
        _polyline(component, [(43, 8), (55, 19), (67, 8)], width=3.0)
        _polyline(component, [(90, -8), (102, -22), (114, -8)], width=3.0)
    elif variant == 3:
        # The same two-cell lattice, but each mixing column is a multimode
        # interference body rather than a directional interaction window.
        rail_ys = (-8.0, 8.0)
        for y in rail_ys:
            _segment(component, (0, y), (156, y), width=3.0)
        for center in (30.0, 78.0, 126.0):
            _rectangle(component, (center, 0), (18, 24))
        _polyline(component, [(39, 8), (52, 21), (69, 8)], width=3.0)
        _polyline(component, [(87, -8), (101, -21), (117, -8)], width=3.0)
    else:
        raise ReleaseError(f"unsupported L4 interferometer variant: {variant}")
    return x_left, x_right, left, right


def _l4_split_recombine(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 156.0
    left = _spread(inputs, pitch=10)
    right = _spread(outputs, pitch=10)
    if variant == 0:
        # Two inputs become four routes through a visible two-stage cascade.
        for y in left:
            _bezier(component, (0, y), dx=29, dy=-y, width=3.0)
        _ellipse(component, (36, 0), (8, 15))
        middle = _spread(4, pitch=11)
        for y in middle:
            _bezier(component, (43, 0), dx=34, dy=y, width=2.8)
        for y in middle:
            _polyline(component, [(77, y), (94, -y), (111, y)], width=2.8)
        for y, target in zip(middle, right, strict=True):
            _bezier(component, (111, y), dx=45, dy=target - y, width=2.8)
    elif variant == 1:
        # First stage is an explicit Y; second stage uses unlike MMI bodies.
        _segment(component, (0, 0), (25, 0), width=3.2)
        for sign in (-1, 1):
            _bezier(component, (25, 0), dx=30, dy=sign * 15, width=3.0)
        _ellipse(component, (62, -15), (7, 10))
        _rectangle(component, (62, 15), (15, 19))
        for node_y, targets in ((-15.0, right[:2]), (15.0, right[2:])):
            for target in targets:
                _bezier(component, (69, node_y), dx=87, dy=target - node_y, width=2.8)
    elif variant == 2:
        # A trident root has three children; only the center child splits
        # again, producing four leaves at mixed depths.
        _segment(component, (0, 0), (28, 0), width=3.2)
        _ellipse(component, (36, 0), (8, 13))
        branch_ys = (-20.0, 0.0, 20.0)
        for y in branch_ys:
            _bezier(component, (43, 0), dx=34, dy=y, width=2.9)
        _segment(component, (77, -20), (156, right[0]), width=2.9)
        _segment(component, (77, 20), (156, right[-1]), width=2.9)
        _rectangle(component, (91, 0), (15, 18))
        _segment(component, (77, 0), (84, 0), width=2.9)
        for target in right[1:3]:
            _bezier(component, (99, 0), dx=57, dy=target, width=2.9)
    else:
        # Three columns of pairwise 2x2 mixers form a four-channel Benes mesh.
        channels = _spread(4, pitch=12)
        for y in channels:
            _segment(component, (0, y), (20, y), width=2.8)
            _segment(component, (136, y), (156, y), width=2.8)
        pairings = ((0, 1, 2, 3), (0, 2, 1, 3), (0, 1, 2, 3))
        x_columns = (38.0, 78.0, 118.0)
        previous_x = 20.0
        current_y = list(channels)
        for x, ordering in zip(x_columns, pairings, strict=True):
            targets = [channels[index] for index in ordering]
            for y0, y1 in zip(current_y, targets, strict=True):
                _polyline(
                    component,
                    [
                        (previous_x, y0),
                        ((previous_x + x) / 2, y0),
                        (x, y1),
                    ],
                    width=2.8,
                )
            for pair in ((0, 1), (2, 3)):
                center_y = (targets[pair[0]] + targets[pair[1]]) / 2
                _ellipse(component, (x + 4, center_y), (5, 7))
            previous_x = x + 8
            current_y = targets
        for y0, y1 in zip(current_y, channels, strict=True):
            _polyline(
                component,
                [(previous_x, y0), (131, y0), (136, y1)],
                width=2.8,
            )
    return x_left, x_right, left, right


def _grating_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 122.0
    left = _spread(inputs, pitch=12)
    right = _spread(outputs, pitch=12)
    _segment(component, (0, 0), (24, 0), width=3.2)
    if variant == 0:
        _taper(component, (24, 0), length=25, width1=3.2, width2=18)
        _ellipse(component, (53, 0), (9, 12))
        for index in range(8):
            _ring(
                component,
                (70, 0),
                12 + index * 4.7,
                width=1.9 + index * 0.12,
            )
    elif variant == 1:
        _taper(component, (24, 0), length=34, width1=3.2, width2=38)
        for index in range(12):
            x = 63 + index * 4.8
            height = 28 + index * 0.9
            _rotated_rectangle(
                component,
                (x, 0),
                (2.2 + index * 0.08, height),
                18.0,
            )
    else:
        raise ReleaseError(f"unsupported L4 grating proposal variant: {variant}")
    return x_left, x_right, left, right


def _edge_interface_scene(
    component: gf.Component,
    spec: dict[str, Any],
    variant: int,
) -> tuple[float, float, list[float], list[float]]:
    inputs, outputs = _parse_signature(spec["port_signature"])
    x_left, x_right = 0.0, 138.0
    left = _spread(inputs, pitch=14)
    right = _spread(outputs, pitch=14)
    if variant == 0:
        _segment(component, (0, -9), (20, -9), width=8.0)
        _bezier(component, (20, -9), dx=88, dy=9, width=4.2)
        for index in range(18):
            x = 27 + index * 4.4
            # Match the cubic centerline used by `_bezier` (hook=0).  Each
            # rib starts slightly inside the carrier envelope, so every one
            # is visibly attached instead of merely following a chord.
            t = (x - 20) / 88
            curve_y = -9 + 27 * t**2 - 18 * t**3
            height = 5.0 + index * 0.55
            _rotated_rectangle(
                component,
                (x, curve_y - 0.5 + height / 2),
                (2.1, height),
                0.0,
            )
        _taper(component, (108, 0), length=30, width1=4.2, width2=3.2)
        left, right = [-9.0], [0.0]
    elif variant == 1:
        # A narrow inverse taper is flanked by two open trench rails.  The
        # widening trench spacing, rather than tooth count, is the grammar.
        _segment(component, (0, 0), (18, 0), width=8.0)
        _taper(component, (18, 0), length=82, width1=8.0, width2=1.4)
        for sign in (-1, 1):
            points = [(18, sign * 9), (45, sign * 8), (75, sign * 6), (111, sign * 4)]
            _polyline(component, points, width=4.2)
        _taper(component, (100, 0), length=38, width1=1.4, width2=3.2)
    else:
        raise ReleaseError(f"unsupported L4 edge-interface variant: {variant}")
    return x_left, x_right, left, right


SceneBuilder = Callable[
    [gf.Component, dict[str, Any], int],
    tuple[float, float, list[float], list[float]],
]


def _wrap(
    function: Callable[..., tuple[float, float, list[float], list[float]]],
    /,
    **kwargs: Any,
) -> SceneBuilder:
    def builder(
        component: gf.Component,
        spec: dict[str, Any],
        variant: int,
    ) -> tuple[float, float, list[float], list[float]]:
        return function(component, spec, variant, **kwargs)

    return builder


SCENE_BUILDERS: dict[str, SceneBuilder] = {
    "l1_underbridged_operation": _l1_underbridged_operation,
    "l1_port_operation": _l1_port_operation,
    "l2_split_rejoin": _wrap(_split_rejoin, hierarchical=False),
    "l2_coupling": _wrap(_coupling_scene, hierarchical=False),
    "l2_bus_loop": _wrap(_bus_loop_scene, hierarchical=False),
    "l2_route_bank": _wrap(_crossing_scene, hierarchical=False),
    "l2_body_terminal": _wrap(_body_terminal_scene, fpr=False),
    "l2_repeated_media": _wrap(_repeated_media_scene, hierarchical=False),
    "l3_coupling_system": _wrap(_coupling_scene, hierarchical=True),
    "l3_interferometer": _l3_interferometer_scene,
    "l3_resonator_graph": _l3_resonator_scene,
    "l3_repeated_media": _wrap(_repeated_media_scene, hierarchical=True),
    "l3_fpr_bank": _l3_fpr_scene,
    "l3_crossing_system": _l3_lattice_scene,
    "l3_mode_evolution": _l3_mode_scene,
    "l3_mux_hierarchy": _l3_mux_hierarchy,
    "l4_awg": _l4_awg_scene,
    "l4_filter_graph": _resonant_filter_scene,
    "l4_multiport_repeated": _l4_multiport_repeated_scene,
    "l4_interferometer_loop": _l4_interferometer_loop,
    "l4_mode_mux": _l4_mode_mux_scene,
    "l4_split_recombine": _l4_split_recombine,
    "l4_grating": _grating_scene,
    "l4_edge_interface": _edge_interface_scene,
}


def build_proposal_scene(spec: dict[str, Any]) -> gf.Component:
    """Build one proposal-only GDSFactory component from its registry record."""

    scene = spec.get("scene")
    if not isinstance(scene, dict):
        raise ReleaseError(f"{spec.get('candidate_id')}: missing scene specification")
    archetype = str(scene.get("archetype", ""))
    variant = scene.get("variant")
    if archetype not in SCENE_BUILDERS:
        raise ReleaseError(
            f"{spec.get('candidate_id')}: unknown scene archetype {archetype!r}"
        )
    if isinstance(variant, bool) or not isinstance(variant, int) or variant < 0:
        raise ReleaseError(f"{spec.get('candidate_id')}: invalid scene variant")
    inputs, outputs = _parse_signature(spec.get("port_signature"))
    component = gf.Component(name=f"proposal_{spec['candidate_id']}")
    x_left, x_right, left_ys, right_ys = SCENE_BUILDERS[archetype](
        component,
        spec,
        variant,
    )
    if len(left_ys) != inputs or len(right_ys) != outputs:
        # A scene may contain additional internal rails, but its externally
        # declared terminal bank must remain exact.
        left_ys = _spread(inputs)
        right_ys = _spread(outputs)
    _boundary_ports(
        component,
        inputs=inputs,
        outputs=outputs,
        x_left=x_left,
        x_right=x_right,
        left_ys=left_ys,
        right_ys=right_ys,
    )
    return component


def _polygon_points(
    component: gf.Component,
    *,
    layer: tuple[int, int] = LAYER,
    required: bool = True,
) -> list[np.ndarray]:
    polygons = component.get_polygons(by="tuple").get(layer, [])
    result: list[np.ndarray] = []
    for polygon in polygons:
        points = np.array(
            [(point.x / 1000.0, point.y / 1000.0) for point in polygon.each_point_hull()],
            dtype=np.float64,
        )
        if points.shape[0] >= 3:
            result.append(points)
    if required and not result:
        raise ReleaseError("proposal scene produced no material polygons")
    return result


def render_proposal_scene(
    spec: dict[str, Any],
    *,
    size: tuple[int, int] = CANVAS_SIZE,
) -> RenderedProposalScene:
    """Render one proposal using independent x/y maximum-visibility scaling."""

    if min(size) < 128:
        raise ReleaseError(f"proposal canvas is too small: {size}")
    component = build_proposal_scene(spec)
    polygons = _polygon_points(component)
    voids = _polygon_points(component, layer=VOID_LAYER, required=False)
    all_points = np.concatenate(polygons, axis=0)
    minimum = all_points.min(axis=0)
    maximum = all_points.max(axis=0)
    extent = maximum - minimum
    if np.any(extent <= 0):
        raise ReleaseError(f"{spec.get('candidate_id')}: degenerate scene footprint")

    scale_x = (size[0] - 2 * CANVAS_MARGIN) / float(extent[0])
    scale_y = (size[1] - 2 * CANVAS_MARGIN) / float(extent[1])
    high_size = (size[0] * ANTIALIAS, size[1] * ANTIALIAS)
    image = Image.new("L", high_size, 255)
    draw = ImageDraw.Draw(image)
    for polygon in polygons:
        points = [
            (
                (
                    CANVAS_MARGIN
                    + (float(x) - float(minimum[0])) * scale_x
                )
                * ANTIALIAS,
                (
                    CANVAS_MARGIN
                    + (float(maximum[1]) - float(y)) * scale_y
                )
                * ANTIALIAS,
            )
            for x, y in polygon
        ]
        draw.polygon(points, fill=0)
    for polygon in voids:
        points = [
            (
                (
                    CANVAS_MARGIN
                    + (float(x) - float(minimum[0])) * scale_x
                )
                * ANTIALIAS,
                (
                    CANVAS_MARGIN
                    + (float(maximum[1]) - float(y)) * scale_y
                )
                * ANTIALIAS,
            )
            for x, y in polygon
        ]
        draw.polygon(points, fill=255)
    image = image.resize(size, Image.Resampling.LANCZOS).convert("RGB")
    return RenderedProposalScene(
        image=image,
        bbox_um=(
            (round(float(minimum[0]), 6), round(float(minimum[1]), 6)),
            (round(float(maximum[0]), 6), round(float(maximum[1]), 6)),
        ),
        display_scale_px_per_um=(round(scale_x, 8), round(scale_y, 8)),
        port_count=len(component.ports),
        port_names=tuple(sorted(str(port.name) for port in component.ports)),
        normalized_d4_sha256=normalized_d4_sha256(image),
    )


# Compiler-facing name.  Keeping the builder separate from the renderer also
# makes it explicit that the compiler owns the review raster and telemetry.
build_proposal = build_proposal_scene


__all__ = [
    "CANVAS_SIZE",
    "RenderedProposalScene",
    "SCENE_BUILDERS",
    "build_proposal",
    "build_proposal_scene",
    "render_proposal_scene",
]
