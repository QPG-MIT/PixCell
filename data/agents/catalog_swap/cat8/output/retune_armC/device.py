"""Symmetric sidewall Bragg grating (rectangular-corrugated strip waveguide).

Primitives-only, parametric recreation of experiments/catalog_swap/cat8/device_bw.png.
The waveguide width square-wave modulates between a wide and a narrow value about a
common centerline, N periods long. Built from butted, centered rectangles only.

gdsfactory 9.20.7, geometry on layer (1, 0).
"""
import gdsfactory as gf

# ---- FUNCTION-DEFINING TUNABLES (top-level) ----
period_um = 0.32090        # Bragg period Lambda -> sets Bragg wavelength (soi220 tune)
num_periods = 19           # grating length N -> reflectivity / bandwidth
w0_um = 0.500              # nominal (mean) waveguide width -> n_eff, single-mode
corrugation_um = 0.099     # full width swing dw = w_wide - w_narrow -> kappa
duty_cycle = 0.5125        # fraction of each period at the WIDE width
layer = (1, 0)

# ---- derived ----
w_wide = w0_um + corrugation_um / 2.0
w_narrow = w0_um - corrugation_um / 2.0
len_wide = period_um * duty_cycle
len_narrow = period_um * (1.0 - duty_cycle)


@gf.cell
def bragg_grating(
    period_um: float = period_um,
    num_periods: int = num_periods,
    w0_um: float = w0_um,
    corrugation_um: float = corrugation_um,
    duty_cycle: float = duty_cycle,
    layer=layer,
) -> gf.Component:
    c = gf.Component()
    ww = w0_um + corrugation_um / 2.0
    wn = w0_um - corrugation_um / 2.0
    lw = period_um * duty_cycle
    ln = period_um * (1.0 - duty_cycle)

    wide = gf.components.rectangle(size=(lw, ww), layer=layer, centered=True)
    narrow = gf.components.rectangle(size=(ln, wn), layer=layer, centered=True)

    # Target grating begins with a NARROW segment, then WIDE, per period.
    x = 0.0
    for _ in range(num_periods):
        rn = c.add_ref(narrow)
        rn.move((x + ln / 2.0, 0.0))
        x += ln
        rw = c.add_ref(wide)
        rw.move((x + lw / 2.0, 0.0))
        x += lw
    return c


if __name__ == "__main__":
    import json
    from pathlib import Path

    c = bragg_grating()
    # with_metadata=False -> no $$$CONTEXT_INFO$$$ wrapper, so the component stays
    # the top-level cell and the evaluator's layer-(1,0) bbox reader can see it.
    c.write_gds("device.gds", with_metadata=False)

    # Measurement contract: emit lengths.json next to the GDS, computed from the
    # module-level tunables (the two grating widths and the period the evaluator
    # needs for the first-order Bragg condition lambda_B = 2 * n_avg * Lambda).
    payload = {
        "grating": {
            "period_um": period_um,
            "w1_um": w_wide,
            "w2_um": w_narrow,
        }
    }
    Path("lengths.json").write_text(json.dumps(payload, indent=2))
    print("wrote device.gds; total length um =", period_um * num_periods)
