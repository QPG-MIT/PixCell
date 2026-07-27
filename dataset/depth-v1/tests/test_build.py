"""Focused tests for the depth-v1 all-anchor qualification barrier."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build  # noqa: E402


def _complete(anchor_id: str) -> build._PreparedAnchor:
    return build._PreparedAnchor(
        anchor_id=anchor_id,
        grammar_id=f"grammar/{anchor_id}",
        contract_record={},
        plan_record={},
        descendants=tuple({} for _ in range(7)),
        outcome="complete",
    )


def _anchor_only(anchor_id: str, *, stage: str = "axis_qualification"):
    failure = build._QualificationFailure(
        anchor_id=anchor_id,
        grammar_id=f"grammar/{anchor_id}",
        stage=stage,
        reason=f"{anchor_id} failed",
    )
    return build._PreparedAnchor(
        anchor_id=anchor_id,
        grammar_id=f"grammar/{anchor_id}",
        contract_record={},
        plan_record={},
        descendants=(),
        outcome="anchor_only",
        failure=failure,
    )


def _fatal(anchor_id: str) -> build._PreparedAnchor:
    failure = build._QualificationFailure(
        anchor_id=anchor_id,
        grammar_id=f"grammar/{anchor_id}",
        stage="anchor_runtime",
        reason=f"{anchor_id} failed fatally",
    )
    return build._PreparedAnchor(
        anchor_id=anchor_id,
        grammar_id=f"grammar/{anchor_id}",
        contract_record=None,
        plan_record=None,
        descendants=(),
        outcome="fatal",
        failure=failure,
    )


def _write_frozen_fixture(root: Path, *, payload: bytes = b"frozen") -> None:
    manifest_path = root / "metadata" / "manifest.json"
    artifact_path = root / "factory" / "accepted_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(payload + b"/manifest")
    artifact_path.write_bytes(payload + b"/artifact")
    freeze = {
        "logical_release_sha256": build.FROZEN_LOGICAL_RELEASE_SHA256,
        "manifest": {
            "path": "metadata/manifest.json",
            "sha256": build.depth_sha256_file(manifest_path),
        },
        "reference_artifacts": {
            "factory/accepted_manifest.json": build.depth_sha256_file(
                artifact_path
            ),
        },
    }
    build.write_json(root / "factory" / "freeze.json", freeze)


def _core_freeze_fixture() -> dict:
    return {
        "reference_artifacts": {
            "data/l0/train.parquet": "0" * 64,
            "galleries/all.png": "1" * 64,
            "metadata/catalog.json": "2" * 64,
        },
    }


def test_prepared_anchor_rejects_partial_descendant_groups() -> None:
    with pytest.raises(ValueError, match="seven rows"):
        build._PreparedAnchor(
            anchor_id="partial",
            grammar_id="grammar/partial",
            contract_record={},
            plan_record={},
            descendants=({},),
            outcome="complete",
        )
    with pytest.raises(ValueError, match="retained partial rows"):
        build._PreparedAnchor(
            anchor_id="failed",
            grammar_id="grammar/failed",
            contract_record={},
            plan_record={},
            descendants=({},),
            outcome="anchor_only",
            failure=build._QualificationFailure(
                anchor_id="failed",
                grammar_id="grammar/failed",
                stage="schedule_r04",
                reason="no candidate",
            ),
        )


def test_frozen_logical_release_assertion_rejects_drift() -> None:
    build._assert_frozen_logical_release(
        {
            "logical_release_sha256": (
                build.FROZEN_LOGICAL_RELEASE_SHA256
            ),
        }
    )
    with pytest.raises(build.DepthBuildError, match="logical release digest"):
        build._assert_frozen_logical_release(
            {"logical_release_sha256": "0" * 64}
        )


def test_frozen_replay_guard_accepts_an_exact_replay(tmp_path: Path) -> None:
    output = tmp_path / "output"
    stage = tmp_path / "stage"
    _write_frozen_fixture(output)
    _write_frozen_fixture(stage)
    build._assert_frozen_replay(stage, output)


def test_frozen_replay_guard_rejects_freeze_object_drift(
    tmp_path: Path,
) -> None:
    output = tmp_path / "output"
    stage = tmp_path / "stage"
    _write_frozen_fixture(output)
    _write_frozen_fixture(stage)
    staged_freeze = build._load_freeze(
        stage / "factory" / "freeze.json",
        label="test",
    )
    staged_freeze["logical_release_sha256"] = "0" * 64
    build.write_json(stage / "factory" / "freeze.json", staged_freeze)
    with pytest.raises(build.DepthBuildError, match="freeze object differs"):
        build._assert_frozen_replay(stage, output)


def test_frozen_replay_guard_rejects_drift_without_touching_output(
    tmp_path: Path,
) -> None:
    output = tmp_path / "output"
    stage = tmp_path / "stage"
    _write_frozen_fixture(output)
    _write_frozen_fixture(stage)
    sentinel = output / "keep.txt"
    sentinel.write_bytes(b"committed release remains")
    before = {
        path.relative_to(output): path.read_bytes()
        for path in output.rglob("*")
        if path.is_file()
    }
    (stage / "factory" / "accepted_manifest.json").write_bytes(b"drift")

    with pytest.raises(build.DepthBuildError, match="changed staged artifact"):
        build._assert_frozen_replay(stage, output)

    after = {
        path.relative_to(output): path.read_bytes()
        for path in output.rglob("*")
        if path.is_file()
    }
    assert after == before
    assert sentinel.read_bytes() == b"committed release remains"


def test_gallery_reference_paths_include_every_progression_page() -> None:
    manifest = {
        "overview": "galleries/overview.png",
        "pages": [
            {"path": "galleries/progressions/l0-01.png"},
            {"path": "galleries/progressions/l4-09.png"},
        ],
        "progression_page_count": 2,
    }
    assert build._gallery_reference_paths(manifest) == [
        "galleries/overview.png",
        "galleries/progressions/l0-01.png",
        "galleries/progressions/l4-09.png",
    ]


def test_frozen_replay_rejects_progression_page_drift(tmp_path: Path) -> None:
    output = tmp_path / "output"
    stage = tmp_path / "stage"
    relative = "galleries/progressions/l0-01.png"
    for root in (output, stage):
        _write_frozen_fixture(root)
        page = root / relative
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_bytes(b"frozen progression")
        freeze = build._load_freeze(
            root / "factory" / "freeze.json",
            label="test",
        )
        freeze["reference_artifacts"][relative] = build.depth_sha256_file(page)
        build.write_json(root / "factory" / "freeze.json", freeze)

    (stage / relative).write_bytes(b"drifted progression")
    with pytest.raises(build.DepthBuildError, match="changed staged artifact"):
        build._assert_frozen_replay(stage, output)


@pytest.mark.parametrize(
    "output_kind",
    (
        "equal",
        "ancestor",
        "inside_data",
        "inside_galleries",
        "inside_metadata",
        "inside_core_factory",
        "overlapping_factory_parent",
    ),
)
def test_output_guard_rejects_dataset_and_frozen_core_overlaps(
    tmp_path: Path,
    output_kind: str,
) -> None:
    dataset_root = tmp_path / "checkout" / "dataset"
    dataset_root.mkdir(parents=True)
    outputs = {
        "equal": dataset_root,
        "ancestor": dataset_root.parent,
        "inside_data": dataset_root / "data" / "depth-v1",
        "inside_galleries": dataset_root / "galleries" / "depth-v1",
        "inside_metadata": dataset_root / "metadata" / "depth-v1",
        "inside_core_factory": (
            dataset_root / "factory" / "core-v1" / "depth-v1"
        ),
        "overlapping_factory_parent": dataset_root / "factory",
    }
    with pytest.raises(build.DepthBuildError, match="output"):
        build._assert_safe_output_path(
            dataset_root,
            outputs[output_kind],
            _core_freeze_fixture(),
        )


def test_output_guard_accepts_disjoint_sibling_release(tmp_path: Path) -> None:
    dataset_root = tmp_path / "checkout" / "dataset"
    dataset_root.mkdir(parents=True)
    build._assert_safe_output_path(
        dataset_root,
        dataset_root / "depth-v1",
        _core_freeze_fixture(),
    )


def test_output_guard_resolves_symlink_aliases(
    tmp_path: Path,
) -> None:
    dataset_root = tmp_path / "checkout" / "dataset"
    protected = dataset_root / "data"
    protected.mkdir(parents=True)
    alias = tmp_path / "data-alias"
    alias.symlink_to(protected, target_is_directory=True)
    with pytest.raises(build.DepthBuildError, match="overlaps"):
        build._assert_safe_output_path(
            dataset_root,
            alias / "depth-v1",
            _core_freeze_fixture(),
        )


def test_inventory_barrier_aggregates_all_failure_kinds() -> None:
    prepared = [_complete(f"anchor-{index:03d}") for index in range(544)]
    prepared.extend(
        (
            _complete("expected-anchor-only"),
            _anchor_only("unexpected-anchor-only", stage="schedule_r06"),
            _fatal("fatal-anchor"),
        )
    )
    with pytest.raises(build.DepthBuildError) as caught:
        build._assert_frozen_qualification_inventory(
            prepared,
            expected_anchor_only=frozenset({"expected-anchor-only"}),
        )
    message = str(caught.value)
    assert "unexpected-anchor-only" in message
    assert "schedule_r06" in message
    assert "expected-anchor-only" in message
    assert "fatal-anchor" in message
    assert "anchor_runtime" in message


def test_inventory_barrier_accepts_one_exact_frozen_inventory() -> None:
    prepared = [_complete(f"anchor-{index:03d}") for index in range(546)]
    prepared.append(_anchor_only("frozen-anchor-only"))
    build._assert_frozen_qualification_inventory(
        prepared,
        expected_anchor_only=frozenset({"frozen-anchor-only"}),
    )


def test_prepare_all_anchors_does_not_stop_at_an_unschedulable_anchor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    anchors = [
        {"id": f"anchor-{index:03d}", "grammar_id": f"grammar-{index:03d}"}
        for index in range(build.APPROVED_REPRESENTATION_COUNT)
    ]
    visited: list[str] = []

    def prepare(anchor, *, grammar_index):
        assert grammar_index == len(visited)
        anchor_id = str(anchor["id"])
        visited.append(anchor_id)
        if grammar_index in {2, 401}:
            return _anchor_only(anchor_id)
        return _complete(anchor_id)

    monkeypatch.setattr(build, "_prepare_anchor", prepare)
    prepared = build._prepare_all_anchors(anchors)
    assert len(visited) == build.APPROVED_REPRESENTATION_COUNT
    assert len(prepared) == build.APPROVED_REPRESENTATION_COUNT
    assert [item.outcome for item in prepared].count("anchor_only") == 2


def test_materialization_cache_reuses_success_and_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    anchor = {"code": "length_um = 10.0\n"}
    success_calls = 0

    def succeed(*args, **kwargs):
        nonlocal success_calls
        success_calls += 1
        return "code", {}, object(), {}, False

    monkeypatch.setattr(build, "_materialize", succeed)
    cache: build._MaterializationCache = {}
    for _ in range(2):
        updates, *_ = build._try_materialize(
            anchor,
            {},
            {"length_um": 8.2},
            anchor_model_png=b"anchor",
            cache=cache,
        )
        assert updates == {"length_um": 8.2}
    assert success_calls == 1

    failure_calls = 0

    def fail(*args, **kwargs):
        nonlocal failure_calls
        failure_calls += 1
        raise build.DepthBuildError("rejected")

    monkeypatch.setattr(build, "_materialize", fail)
    failure_cache: build._MaterializationCache = {}
    with pytest.raises(build.DepthBuildError, match="rejected"):
        build._try_materialize(
            anchor,
            {},
            {"length_um": 8.2},
            anchor_model_png=b"anchor",
            cache=failure_cache,
        )
    first_failure_calls = failure_calls
    assert first_failure_calls > 1
    with pytest.raises(build.DepthBuildError, match="rejected"):
        build._try_materialize(
            anchor,
            {},
            {"length_um": 8.2},
            anchor_model_png=b"anchor",
            cache=failure_cache,
        )
    assert failure_calls == first_failure_calls


@pytest.mark.parametrize(
    ("derived_ports", "expected_executions"),
    ((False, 1), (True, 2)),
)
def test_materialize_executes_once_without_derived_ports(
    monkeypatch: pytest.MonkeyPatch,
    derived_ports: bool,
    expected_executions: int,
) -> None:
    literal_map = {"length_um": 10.0}
    if derived_ports:
        literal_map["optical_port_specs"] = []
    executions = 0
    candidate_runtime = {"bbox_span_um": [12.0, 2.0]}
    anchor_runtime = {"bbox_span_um": [10.0, 2.0]}

    def execute(*args, **kwargs):
        nonlocal executions
        executions += 1
        return candidate_runtime

    monkeypatch.setattr(build, "rewrite_parameters", lambda code, updates: code)
    monkeypatch.setattr(build, "_semantic_relation_errors", lambda before, after: [])
    monkeypatch.setattr(build, "_literal_map", lambda code: literal_map)
    monkeypatch.setattr(build, "_rewrite_literals", lambda code, updates: code)
    monkeypatch.setattr(build, "execute_program", execute)
    monkeypatch.setattr(
        build,
        "derive_optical_port_specs",
        lambda anchor, candidate: [],
    )
    monkeypatch.setattr(
        build,
        "_source_gate",
        lambda before, after, expected_changed: {},
    )
    monkeypatch.setattr(
        build,
        "validate_candidate",
        lambda anchor, candidate, **kwargs: SimpleNamespace(
            passed=True,
            errors=(),
        ),
    )

    build._materialize(
        {"code": "ignored", "level": "L0"},
        anchor_runtime,
        {"length_um": 12.0},
        anchor_model_png=b"anchor",
    )
    assert executions == expected_executions


def test_repeat_count_witness_binds_emitted_polygon_count() -> None:
    code = "rows = 2\ncolumns = 3\n"
    runtime = {"structural_metrics": {"polygon_count": 6}}
    build._validate_repeated_element_count(
        code,
        runtime,
        {"rows", "columns"},
    )
    runtime["structural_metrics"]["polygon_count"] = 5
    with pytest.raises(build.DepthBuildError, match="geometry witness differs"):
        build._validate_repeated_element_count(
            code,
            runtime,
            {"rows", "columns"},
        )


def test_slot_failure_discards_all_previously_prepared_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = build.ParameterAxis(
        axis_id="axis/x",
        names=("x",),
        parameter_class="realization_continuous_dimension",
        priority=0,
        dependency_kind="independent",
    )
    contract = build.ParameterContract(
        anchor_id="anchor",
        grammar_id="grammar",
        schedule_version="test",
        source_grammar_hash="a" * 64,
        assignments=(),
        axes=(axis,),
        reference_scale_um=1.0,
        declared_parameter_names=("x",),
    )
    specs = tuple(
        build.CandidateSpec(
            slot=f"r{slot:02d}",
            role="primary",
            direction="high",
            updates=(("x", slot),),
            axis_ids=(axis.axis_id,),
            factors=((axis.axis_id, 1.0),),
            structural_count_deltas=(),
            fallback=False,
        )
        for slot in range(1, 8)
    )
    anchor = {
        "id": "anchor",
        "grammar_id": "grammar",
        "level": "L1",
        "code": "x = 0\n",
        "image_sha256": "anchor-image",
        "instruction": "anchor-instruction",
    }

    monkeypatch.setattr(
        build,
        "execute_program",
        lambda code, isolation: {"ports": []},
    )
    monkeypatch.setattr(
        build,
        "render_geometry",
        lambda runtime, mode: SimpleNamespace(png_bytes=b"anchor"),
    )
    monkeypatch.setattr(
        build,
        "gate_ports",
        lambda runtime, **kwargs: SimpleNamespace(passed=True, errors=()),
    )
    monkeypatch.setattr(build, "classify_parameters", lambda code, row: contract)
    monkeypatch.setattr(build, "_coalesce_equal_shape_axes", lambda value: value)
    monkeypatch.setattr(
        build,
        "_qualify_axes",
        lambda *args, **kwargs: (axis,),
    )
    monkeypatch.setattr(build, "candidate_specs", lambda value: specs)
    monkeypatch.setattr(build, "_literal_map", lambda code: {"x": 0})
    monkeypatch.setattr(
        build,
        "_candidate_attempts",
        lambda anchor_values, target: [dict(target)],
    )

    def materialize(anchor, anchor_runtime, updates, **kwargs):
        value = int(updates["x"])
        if value == 4:
            return build._MaterializationFailure("slot four failed")
        return build._MaterializationSuccess(
            updates=(("x", value),),
            code=f"x = {value}\n",
            runtime={},
            report=object(),
            source_evidence={},
            derived_ports=False,
        )

    monkeypatch.setattr(build, "_cached_materialization", materialize)

    def descendant(anchor, *, slot, **kwargs):
        return {
            "image_sha256": f"image-{slot}",
            "instruction": f"instruction-{slot}",
            "code_sha256": f"code-{slot}",
            "controlled_axes": ["x"],
            "geometry_id": f"geometry-{slot}",
            "parameter_delta_json": "{}",
            "realization_id": f"r{slot:02d}",
            "target_image_sha256": f"target-{slot}",
            "verification_evidence_json": "{}",
        }

    monkeypatch.setattr(build, "_descendant_row", descendant)
    prepared = build._prepare_anchor(anchor, grammar_index=0)
    assert prepared.outcome == "anchor_only"
    assert prepared.descendants == ()
    assert prepared.plan_record == {
        "anchor_id": "anchor",
        "grammar_id": "grammar",
        "level": "L1",
        "states": [],
    }
    assert prepared.failure is not None
    assert prepared.failure.stage == "schedule_r04"
    assert prepared.failure.reason == "slot four failed"
