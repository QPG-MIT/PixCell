"""1x4 MMI splitter - primitives only, parametric."""
import gdsfactory as gf
from gdsfactory.typings import LayerSpec

# ===== TUNABLES (function-defining knobs) =====
mmi_width = 17.0         # MMI body width (µm)
mmi_length = 5.5         # MMI body length (µm) - determines imaging
taper_length = 3.0       # Output taper length (µm)
taper_tip_width = 0.8    # Output taper tip width (µm)
taper_base_width = 2.5   # Output taper base at MMI junction (µm)
output_pitch = 4.2       # Center-to-center spacing of output tapers (µm)
input_taper_length = 1.5 # Input taper length (µm)
input_taper_tip_width = 0.8  # Input taper tip width (µm)
input_taper_base_width = 2.5 # Input taper base width (µm)

# Layer
LAYER: LayerSpec = (1, 0)


@gf.cell(check_instances=False)
def mmi_1x4(
    _mmi_width: float = None,
    _mmi_length: float = None,
    _taper_length: float = None,
    _taper_tip_width: float = None,
    _taper_base_width: float = None,
    _output_pitch: float = None,
    _input_taper_length: float = None,
    _input_taper_tip_width: float = None,
    _input_taper_base_width: float = None,
) -> gf.Component:
    # Use passed params or fall back to module-level tunables
    w = _mmi_width if _mmi_width is not None else mmi_width
    l = _mmi_length if _mmi_length is not None else mmi_length
    tl = _taper_length if _taper_length is not None else taper_length
    ttw = _taper_tip_width if _taper_tip_width is not None else taper_tip_width
    tbw = _taper_base_width if _taper_base_width is not None else taper_base_width
    op = _output_pitch if _output_pitch is not None else output_pitch
    itl = _input_taper_length if _input_taper_length is not None else input_taper_length
    ittw = _input_taper_tip_width if _input_taper_tip_width is not None else input_taper_tip_width
    itbw = _input_taper_base_width if _input_taper_base_width is not None else input_taper_base_width

    c = gf.Component()

    # Build device centered at origin
    # Total height = input_taper_length + mmi_length + taper_length
    total_height = itl + l + tl

    # Y positions (centered around y=0)
    input_tip_y = -total_height / 2
    input_base_y = input_tip_y + itl
    mmi_bottom_y = input_base_y
    mmi_top_y = mmi_bottom_y + l
    output_tip_y = mmi_top_y + tl

    # MMI body - centered horizontally
    mmi_body = c << gf.components.rectangle(
        size=(w, l),
        layer=LAYER,
        centered=True
    )
    mmi_body.dmove((0, (mmi_bottom_y + mmi_top_y) / 2))

    # 4 output tapers at top of MMI - symmetric positions
    output_positions = [
        -1.5 * op,
        -0.5 * op,
        0.5 * op,
        1.5 * op
    ]

    for x_pos in output_positions:
        # Build taper as polygon for precise control
        half_base = tbw / 2
        half_tip = ttw / 2
        c.add_polygon(
            [
                (x_pos - half_base, mmi_top_y),
                (x_pos + half_base, mmi_top_y),
                (x_pos + half_tip, output_tip_y),
                (x_pos - half_tip, output_tip_y),
            ],
            layer=LAYER
        )

    # Input taper at bottom (single, centered)
    half_base_in = itbw / 2
    half_tip_in = ittw / 2
    c.add_polygon(
        [
            (-half_tip_in, input_tip_y),
            (half_tip_in, input_tip_y),
            (half_base_in, input_base_y),
            (-half_base_in, input_base_y),
        ],
        layer=LAYER
    )

    return c


if __name__ == "__main__":
    c = mmi_1x4()
    c.write_gds("experiments/paper_swap/final2/output/recreation_opus45m/device.gds")
    print(f"Wrote GDS: {c.name}")
