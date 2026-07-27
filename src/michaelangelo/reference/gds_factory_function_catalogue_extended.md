# GDSFactory Parametric Primitives Catalogue

## 1. Waveguide Primitives

Basic building blocks for constructing waveguide geometry:

| Function | Key Parameters | Description |
|----------|----------------|-------------|
| `gf.components.straight(length=10, cross_section=xs)` | `length`, `cross_section` | Straight waveguide segment. |
| `gf.components.bend_euler(radius=10, angle=90, p=0.5, cross_section=xs)` | `radius`, `angle`, `p`, `cross_section` | Euler bend with adiabatic curvature transition. |
| `gf.components.bend_circular(radius=10, angle=90, cross_section=xs)` | `radius`, `angle`, `cross_section` | Circular arc bend with constant radius. |
| `gf.components.bend_s(size=(10, 10), cross_section=xs)` | `size`, `cross_section` | S-bend connecting offset waveguides. Size is (dx, dy). |
| `gf.components.bezier(control_points=[(0, 0), (5, 0), (5, 1.8), (10, 1.8)], cross_section=xs)` | `control_points`, `cross_section` | Cubic Bézier waveguide component. |
| `gf.components.taper(length=10, width1=0.5, width2=1.0)` | `length`, `width1`, `width2` | Linear width transition between two widths. |
| `gf.components.coupler_straight(length=10, gap=0.2, cross_section=xs)` | `length`, `gap`, `cross_section` | Two parallel straight waveguides with specified gap. |

---

## 2. Basic Shapes

Geometric primitives for arbitrary polygon construction:

| Function | Key Parameters | Description |
|----------|----------------|-------------|
| `gf.components.rectangle(size=(10, 5), layer=(1, 0), centered=False)` | `size`, `layer`, `centered` | Rectangle. With `centered=False`, its lower-left corner is at the origin; with `centered=True`, its center is at the origin. |
| `gf.components.circle(radius=10, layer=(1, 0))` | `radius`, `layer` | Circular shape. |
| `gf.components.ring(width=0.5, radius=10, layer=(1, 0))` | `width`, `radius`, `layer` | Annular ring shape (geometric, not resonator). |
| `gf.components.cross(length=10, width=3, layer=(1, 0))` | `length`, `width`, `layer` | Cross/plus shape. |
| `gf.components.triangle(x=10, y=20, layer=(1, 0))` | `x`, `y`, `layer` | Triangular shape. |
| `gf.components.ellipse(radii=(10, 5), layer=(1, 0))` | `radii`, `layer` | Ellipse with (x_radius, y_radius). |
| `gf.components.regular_polygon(sides=6, side_length=10, layer=(1, 0))` | `sides`, `side_length`, `layer` | N-sided regular polygon (hexagon, octagon, etc). |
| `gf.components.L(width=10, size=(20, 30), layer=(1, 0))` | `width`, `size`, `layer` | L-shaped geometry with arm dimensions. |

---

## 3. Path Functions (Core Parametric System)

The path system is the TRUE parametric construction method. Create paths, then extrude them:

### Path Creation

| Function | Key Parameters | Description |
|----------|----------------|-------------|
| `gf.Path(points)` | list of (x, y) tuples | Create path from arbitrary coordinates. |
| `gf.path.straight(length=10)` | `length` | Straight path segment. |
| `gf.path.arc(radius=10, angle=90)` | `radius`, `angle` | Circular arc path. |
| `gf.path.euler(radius=10, angle=90, p=0.5)` | `radius`, `angle`, `p` | Euler spiral path (adiabatic curvature). |
| `gf.path.smooth(points, radius=4.0)` | `points`, `radius` | Smooth path from waypoints with automatic bends. |
| `gf.path.spiral_archimedean(min_bend_radius, separation, number_of_loops, npoints)` | `min_bend_radius`, `separation`, `number_of_loops`, `npoints` | Archimedean spiral path. |

### Path Extrusion

| Function | Key Parameters | Description |
|----------|----------------|-------------|
| `gf.path.extrude(p=path, cross_section=xs)` | `p`, `cross_section` | Convert path to component with constant width. |
| `gf.path.extrude_transition(p=path, transition=transition)` | `p`, `transition` | Extrude path with varying width. |
| `gf.path.transition(cross_section1=xs1, cross_section2=xs2, width_type='sine')` | `cross_section1`, `cross_section2`, `width_type` | Create width transition between two cross-sections. |


## 4. Boolean Operations

Combine or subtract geometry:

| Function | Key Parameters | Description |
|----------|----------------|-------------|
| `gf.boolean(A, B, operation="or", layer=(1, 0))` | `A`, `B`, `operation`, `layer` | Boolean: "or", "and", "not", "xor" |

**Example — Create a concentric hollow rectangle.**

Boolean operations preserve the operands' existing coordinates. Both rectangles are therefore centered on the same origin before subtraction:

```python
outer = gf.components.rectangle(size=(20, 10), layer=(1, 0), centered=True)
inner = gf.components.rectangle(size=(16, 6), layer=(1, 0), centered=True)
frame = gf.boolean(outer, inner, operation="not", layer=(1, 0))
```

---

## 5. Component Assembly Pattern

The standard pattern for building complex devices from primitives:

```python
import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # Add primitives as references
    wg = c << gf.components.straight(length=10, cross_section=xs)
    bend = c << gf.components.bend_euler(radius=10, cross_section=xs)

    # Connect ports
    bend.connect("o1", wg.ports["o2"])

    # Expose external ports
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=bend.ports["o2"])

    return c

# Create and save
device = my_device()
device.write_gds("my_device.gds")
```

### Key Assembly Operations

| Operation | Syntax | Description |
|-----------|--------|-------------|
| Add reference | `ref = c << component` | Add component instance to parent. |
| Connect ports | `ref.connect("o1", other.ports["o2"])` | Align and connect two optical ports. |
| Add port | `c.add_port("name", port=ref.ports["o1"])` | Expose internal port externally. |
| Move | `ref.move((x, y))` | Translate component. |
| Rotate | `ref.rotate(angle)` | Rotate component (degrees). |
| Mirror | `ref.mirror()` | Mirror component. |
| Add array | `array_ref = c.add_ref(component, columns=3, rows=2, column_pitch=10, row_pitch=20)` | Add a regular array of component references. |

---

## 6. Routing

Auto-route between ports:

| Function | Key Parameters | Description |
|----------|----------------|-------------|
| `gf.routing.route_single(component, port1, port2, cross_section=xs)` | `component`, `port1`, `port2`, `cross_section` | Adds a route between two ports directly to the parent component and returns a `ManhattanRoute`. |
