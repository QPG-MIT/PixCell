"""conductor.fom — the three-source FoM resolution (function pipeline)."""

from homi.conductor.fom import DEVICE_FOMS, classify_text, resolve_fom


def test_classify_specific_before_generic():
    assert classify_text("a focusing grating coupler for fiber arrays") == "grating_coupler"
    assert classify_text("apodized Bragg grating in SOI") == "bragg"
    assert classify_text("unbalanced Mach-Zehnder interferometer") == "mzi"
    assert classify_text("a 1x4 power splitter based on multimode interference") == "mmi"
    assert classify_text("racetrack resonator add-drop filter") == "ring"
    assert classify_text("no photonics here") is None
    assert classify_text(None) is None


def test_resolve_precedence_and_conflicts():
    plan = resolve_fom(
        human="I want the MZI to hit 8nm FSR",
        paper="a 1x4 power splitter in slot waveguides",
        visual="single-input four-output multimode splitter",
    )
    assert plan.device_class == "mzi"            # human wins
    assert plan.source == "human"
    assert plan.conflicts                          # paper/visual disagree -> surfaced
    assert any("mmi" in c or "splitter" in c for c in plan.conflicts)

    plan2 = resolve_fom(paper="a 1x4 power splitter (MMI)",
                        visual="four-output multimode splitter or star-coupler")
    assert plan2.source == "paper"
    assert plan2.device_class == "mmi"
    assert plan2.conflicts == []                   # both classify the same family


def test_targets_fill_spec_template():
    plan = resolve_fom(human="mzi", targets={"fsr_nm": 8.0, "not_a_metric": 1})
    assert plan.spec_template["target"]["value"] == 8.0
    # the filled template is a copy — the table itself must stay pristine
    assert DEVICE_FOMS["mzi"]["spec_template"]["target"]["value"] is None


def test_table_specs_match_evaluator_schema():
    for cls, entry in DEVICE_FOMS.items():
        assert entry["fom"] and entry["description"]
        assert entry["in_loop_tier"] in (0, 1)
        template = entry["spec_template"]
        assert ("target" in template) != ("targets" in template)  # exactly one form
        targets = template.get("targets") or [template["target"]]
        for t in targets:
            assert t.get("metric")
            assert {"value", "min", "max"} & t.keys()


def test_no_evidence_returns_none():
    assert resolve_fom() is None
    assert resolve_fom(visual="a mysterious blob") is None
