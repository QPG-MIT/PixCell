"""Weber must see the parametric contract's knobs (module-level tunables).

Regression for the explorer-audit fix: get_parameter_info_for_ui returned []
for contract-shaped scripts (knobs as top-level `name = value`), which starved
the marimo workbench, MCP parameter suggestions, AND the JEE optimizer.
"""

import textwrap

CONTRACT_SCRIPT = textwrap.dedent(
    """
    import gdsfactory as gf

    layer = (1, 0)
    length_um = 10.0
    width_um = 2.0
    unused_note_um = 99.0  # assigned but never consumed

    @gf.cell
    def device() -> gf.Component:
        c = gf.Component()
        r = gf.components.rectangle(size=(length_um, width_um), layer=layer)
        c.add_ref(r)
        return c

    if __name__ == "__main__":
        device().write_gds("device.gds")
    """
)


def test_parameter_info_includes_top_level_tunables():
    from homi.weber_integration import analyze_and_configure, get_parameter_info_for_ui

    _analysis, slot_config = analyze_and_configure(CONTRACT_SCRIPT)
    params = get_parameter_info_for_ui(slot_config)
    names = {p["name"] for p in params}
    assert {"length_um", "width_um"} <= names
    by_name = {p["name"]: p for p in params}
    assert abs(by_name["length_um"]["default_value"] - 10.0) < 1e-9


def test_tunable_parameters_include_module_level():
    from weber.core.analyzer import analyze_script_from_source

    analysis = analyze_script_from_source(CONTRACT_SCRIPT)
    names = {p.name for p in analysis.get_tunable_parameters()}
    assert {"length_um", "width_um"} <= names


LOOP_SCRIPT = textwrap.dedent(
    """
    import gdsfactory as gf

    layer = (1, 0)

    @gf.cell
    def device() -> gf.Component:
        c = gf.Component()
        body = gf.components.rectangle(size=(10.0, 4.0), layer=layer)
        c.add_ref(body)
        for i in range(3):
            arm = gf.components.rectangle(
                size=(2.0, 0.5),
                layer=layer,
            )
            r = c.add_ref(arm)
            r.dmovey(i * 1.5)
        return c
    """
)


def test_layer_call_interceptor_retargets_per_slot_loop_safe(tmp_path):
    """Per-slot layer assignment on a contract script (layer=layer kwargs,
    multi-line call, loop-instantiated slot): all instances retarget; the
    unassigned slot stays on (1,0); geometry is unchanged."""
    import gdsfactory as gf
    import gdstk

    from homi.weber_integration import analyze_and_configure, layer_call_interceptor

    _analysis, slots = analyze_and_configure(LOOP_SCRIPT)
    cmap = {s.slot_id: s.component_ids for s in slots.slots}
    assert "arm" in cmap and "body" in cmap

    def build(assignments):
        try:
            gf.clear_cache()
        except Exception:
            pass
        ns = {"gf": gf, "__name__": "__test__"}
        with layer_call_interceptor(_analysis, cmap, assignments):
            exec(LOOP_SCRIPT, ns)
            comp = ns["device"]()
        # count flattened instances per layer from the component itself
        # (GDS round-trips hit kfactory's CONTEXT_INFO reference maze).
        # get_polygons() keys are kfactory layer INDICES — map via the layout
        # table to real GDS (layer, datatype).
        layers = {}
        for idx, plist in comp.get_polygons().items():
            info = comp.kcl.layout.get_info(idx)
            layers[(info.layer, info.datatype)] = len(plist)
        return layers

    base = build({})
    assert set(base) == {(1, 0)}

    split = build({"arm": (2, 0)})
    assert (2, 0) in split and (1, 0) in split
    assert split[(2, 0)] == 3          # all three loop instances retargeted
    assert sum(split.values()) == sum(base.values())  # geometry count unchanged
