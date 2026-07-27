import gdsfactory as gf
from pathlib import Path

# Top-level parametric tunables
wg_width = 0.84
coupler_gap = 0.07
coupling_length = 100.0
num_guides = 6
top_box_length = 12.0
bottom_box_length = 12.0

@gf.cell
def directional_coupler():
    """
    Directional coupler: filled boxes + parallel guides in coupling region.
    """
    c = gf.Component()

    guide_spacing = wg_width + coupler_gap
    vertical_span = (num_guides - 1) * guide_spacing

    # Y positions
    y_coupling_min = 0.0
    y_coupling_max = vertical_span

    section_gap = 0.5
    y_top_max = y_coupling_max + section_gap
    y_top_min = y_top_max + vertical_span

    y_bottom_max = y_coupling_min - section_gap
    y_bottom_min = y_bottom_max - vertical_span

    # X positions
    x_top_left = 0.0
    x_coupling_left = top_box_length
    x_bottom_left = x_coupling_left + coupling_length

    # --- TOP BOX (filled) ---
    top_box_height = vertical_span + wg_width
    top_rect = gf.components.rectangle(
        size=(top_box_length, top_box_height),
        layer=(1, 0)
    )
    ref_top = c.add_ref(top_rect)
    ref_top.move((x_top_left, y_top_min - wg_width/2))

    # --- COUPLING REGION (parallel individual guides) ---
    for i in range(num_guides):
        y = y_coupling_min + i * guide_spacing
        rect = gf.components.rectangle(size=(coupling_length, wg_width), layer=(1, 0))
        ref = c.add_ref(rect)
        ref.move((x_coupling_left, y))

    # --- BOTTOM BOX (filled) ---
    bottom_box_height = vertical_span + wg_width
    bottom_rect = gf.components.rectangle(
        size=(bottom_box_length, bottom_box_height),
        layer=(1, 0)
    )
    ref_bottom = c.add_ref(bottom_rect)
    ref_bottom.move((x_bottom_left, y_bottom_min - wg_width/2))

    return c

if __name__ == "__main__":
    c = directional_coupler()
    c.show()
    gds_path = Path("device.gds")
    c.write_gds(gds_path)
    print(f"GDS written to {gds_path}")

    import json
    lengths = {"coupling_length_um": coupling_length}
    with open("lengths.json", "w") as f:
        json.dump(lengths, f, indent=2)
    print("lengths.json written")
