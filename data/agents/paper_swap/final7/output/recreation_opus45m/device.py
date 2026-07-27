"""Racetrack resonator with dual internal segmented bus waveguides.

Target footprint: width=3.0um, height=5.5um (device is TALLER than wide).
The racetrack has its long axis vertical, with semicircles at top and bottom.
"""
import gdsfactory as gf
from gdsfactory.typings import LayerSpec

# === TUNABLES (function-defining knobs) ===
# Target footprint: 3.0um (width) x 5.5um (height)

# Racetrack ring parameters - restore iteration 7 values
ring_width = 0.58        # waveguide width of the outer ring
ring_radius = 1.21       # bend radius at top/bottom ends
straight_length = 2.56   # length of vertical straight sections

# Bus waveguide parameters (INSIDE the ring, horizontal)
bus_width = 0.32         # width (thickness) of each internal bus waveguide
bus_length = 1.9         # horizontal length of each bus
bus_vert_offset = 0.65   # vertical offset of each bus from center

# Slot parameters (rectangular cutouts in bus waveguides)
slot_width = 0.35        # horizontal width of each slot cutout
slot_length = 0.22       # vertical height of each slot
num_slots = 2            # slots per bus
slot_spacing = 0.55      # center-to-center horizontal spacing

# Layer
LAYER: LayerSpec = (1, 0)


@gf.cell
def racetrack_ring_vertical() -> gf.Component:
    """Create a VERTICAL racetrack ring (long axis along Y)."""
    c = gf.Component()

    path = gf.Path()
    path += gf.path.straight(length=straight_length)
    path += gf.path.arc(radius=ring_radius, angle=180)
    path += gf.path.straight(length=straight_length)
    path += gf.path.arc(radius=ring_radius, angle=180)

    cross_section = gf.cross_section.cross_section(width=ring_width, layer=LAYER)
    ring = c << gf.path.extrude(path, cross_section=cross_section)

    # Rotate 90 degrees to make it vertical
    ring.rotate(90)
    ring.move(ring.center, (0, 0))

    return c


@gf.cell
def segmented_bus() -> gf.Component:
    """Create a single bus waveguide with slot cutouts."""
    c = gf.Component()

    # Main bus rectangle
    bus = c << gf.components.rectangle(size=(bus_length, bus_width), layer=LAYER)
    bus.move(bus.center, (0, 0))

    # Create slots component
    slots = gf.Component()
    total_slot_span = (num_slots - 1) * slot_spacing
    start_x = -total_slot_span / 2

    for i in range(num_slots):
        slot = slots << gf.components.rectangle(size=(slot_width, slot_length), layer=LAYER)
        slot.move(slot.center, (start_x + i * slot_spacing, 0))

    # Boolean subtract slots from bus
    result = gf.boolean(c, slots, operation="not", layer=LAYER)
    return result


@gf.cell
def dual_bus_assembly() -> gf.Component:
    """Create the two internal bus waveguides (vertically separated)."""
    c = gf.Component()

    upper_bus = c << segmented_bus()
    upper_bus.move((0, bus_vert_offset))

    lower_bus = c << segmented_bus()
    lower_bus.move((0, -bus_vert_offset))

    return c


@gf.cell
def racetrack_dual_bus_resonator() -> gf.Component:
    """Main device: vertical racetrack ring with internal dual buses."""
    c = gf.Component()

    ring = c << racetrack_ring_vertical()
    buses = c << dual_bus_assembly()

    return c


if __name__ == "__main__":
    c = racetrack_dual_bus_resonator()
    c.write_gds("experiments/paper_swap/final7/output/recreation_opus45m/device.gds")
    print("Written device.gds")
