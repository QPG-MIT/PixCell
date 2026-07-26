# PixCell `core-v1` coverage audit

Frozen release `e1c509dca337ce485efcb2b35101a052e06b12331b63a2f21a36c93b3682ea89` contains 738 accepted rows and 547 representation grammars.

## Core balance

| Level | Rows | Representations | Concepts | Unique images | Unique D4 | Anchor-only |
|---|---|---|---|---|---|---|
| L0 | 177 | 93 | 22 | 172 | 135 | 61 |
| L1 | 215 | 127 | 24 | 215 | 206 | 54 |
| L2 | 118 | 99 | 19 | 118 | 111 | 80 |
| L3 | 120 | 120 | 20 | 120 | 120 | 120 |
| L4 | 108 | 108 | 108 | 108 | 108 | 108 |

Role balance:

- `calibration`: 10
- `equivariance`: 164
- `realization`: 17
- `semantic`: 547
- 423/547 representations are anchor-only.
- All 228 L3/L4 representations are anchor-only.

## Duplicate and D4 telemetry

- 733 unique images and 680 unique D4 silhouettes.
- 5 exact groups involving 10 rows.
- 41 D4-equivalent groups involving 99 rows.
- Every reported exact/D4 group remains inside one `leakage_group_id`.

## Non-exact review pressure

The following telemetry is deterministic curator triage, not an automatic duplicate or admission gate.

| Aligned silhouette IoU | Anchor pairs | Same family | Different |
|---|---|---|---|
| ≥ 0.70 | 331 | 170 | 161 |
| ≥ 0.80 | 105 | 80 | 25 |
| ≥ 0.90 | 24 | 24 | 0 |
| ≥ 0.95 | 10 | 10 | 0 |

Nearest-neighbor aligned-IoU quantiles across semantic anchors: p50 0.582, p90 0.855, p99 0.959, max 0.977.
The coarse AST skeleton pass finds 474 templates across 547 anchors; 104 rows belong to 31 reused groups.

Highest non-exact/D4 silhouette-pressure pairs:

| Left | Right | IoU | Same family |
|---|---|---|---|
| `l0_02_circle__semantic__disk` | `l0_07_regular_polygon__semantic__sides_12` | 0.977 | True |
| `l0_11_bend_circular__semantic__angle_pos180` | `l0_18_path_arc__semantic__angle_pos180` | 0.966 | True |
| `l0_07_regular_polygon__semantic__sides_12` | `l0_07_regular_polygon__semantic__sides_8` | 0.961 | True |
| `l0_11_bend_circular__semantic__angle_pos270` | `l0_18_path_arc__semantic__angle_pos270` | 0.959 | True |
| `l1_04_center_align__b2__proposal_b` | `l1_06_gap__b2__proposal_b` | 0.959 | True |
| `l0_10_bend_euler__semantic__angle_pos180` | `l0_19_path_euler__semantic__angle_pos180` | 0.958 | True |
| `l0_10_bend_euler__semantic__angle_pos135` | `l0_19_path_euler__semantic__angle_pos135` | 0.956 | True |
| `l0_11_bend_circular__semantic__angle_pos90` | `l0_18_path_arc__semantic__angle_pos90` | 0.955 | True |
| `l0_11_bend_circular__semantic__angle_pos135` | `l0_18_path_arc__semantic__angle_pos135` | 0.954 | True |
| `l0_10_bend_euler__semantic__angle_pos90_low_p` | `l0_19_path_euler__semantic__angle_pos90_low_p` | 0.953 | True |

## Prerequisite closure

| Bridge | Reached | Edges | Missing concepts |
|---|---|---|---|
| L0 → L1 | 18/22 | 321 | `l0_13_bezier`, `l0_15_coupler_straight`, `l0_16_path_polyline`, `l0_21_path_spiral` |
| L1 → L2 | 24/24 | 298 | None |
| L2 → L3 | 18/19 | 690 | `l2_15_approach_parallel_departure_pair` |
| L3 → L4 | 0/20 | 0 | `l3_01_serial_heterogeneous_chain`, `l3_02_parallel_reconvergent_bundle`, `l3_03_recursive_asymmetric_branch_hierarchy`, `l3_04_persistent_trunk_with_side_branches`, `l3_07_constructive_body_terminal_system`, `l3_08_dual_body_multi_corridor`, `l3_09_closed_subassembly_carrier_relation`, `l3_10_obstacle_constrained_route_bundle`, `l3_11_transition_repeated_transition_spine`, `l3_12_bilateral_graded_carrier`, `l3_13_dual_bank_local_defect`, `l3_14_supercell_array_with_channel_or_defect`, `l3_15_constructive_hub_radial_hierarchy`, `l3_16_multi_axis_hub_terminal_routes`, `l3_17_tangent_contact_hierarchy`, `l3_18_extracted_region_scaffold`, `l3_19_multi_body_routed_assembly`, `l3_20_carrier_through_aperture_system`, `l3_21_branch_coupled_repeated_media`, `l3_22_cyclic_carrier_terminal_graph` |

The largest discontinuity is L3 → L4: no L4 row declares an L3 prerequisite. L2 also leaves the direct coupling precursor `l2_15_approach_parallel_departure_pair` unused at L3.

## Port balance

| Level | Port signature | Rows |
|---|---|---|
| L2 | 0x0 | 72 |
| L2 | 1x1 | 27 |
| L2 | 1x2 | 6 |
| L2 | 2x2 | 13 |
| L4 | 1x0 | 8 |
| L4 | 1x1 | 40 |
| L4 | 1x2 | 13 |
| L4 | 1x3 | 1 |
| L4 | 1x4 | 4 |
| L4 | 2x1 | 1 |
| L4 | 2x2 | 33 |
| L4 | 2x3 | 1 |
| L4 | 2x4 | 1 |
| L4 | 2x5 | 1 |
| L4 | 3x1 | 1 |
| L4 | 3x3 | 3 |
| L4 | 3x4 | 1 |

L2 assigns `0x0` to 72/118 rows. L4 assigns `1x1` or `2x2` to 73/108 rows (67.6%).

## L4 mechanism balance

L4 contains 101 distinct declared mechanisms across 108 rows.

| Template | Rows |
|---|---|
| component | 8 |
| converter | 14 |
| coupler | 18 |
| crossing | 8 |
| fan | 3 |
| interferometer | 8 |
| repeated | 18 |
| resonator | 18 |
| splitter | 13 |

Family balance:

| Family | Rows | Unique mechanisms | Ports |
|---|---|---|---|
| Adiabatic Multi Rail Couplers | 6 | 6 | 1x2: 1, 2x2: 3, 3x3: 2 |
| Bragg Swg Repeated Media | 7 | 6 | 1x1: 7 |
| Branch Junction Splitters | 5 | 5 | 1x2: 4, 1x3: 1 |
| Conventional Directional Couplers | 6 | 5 | 2x2: 6 |
| Coupled Structured Loop Resonators | 6 | 6 | 1x1: 6 |
| Curved Mixed Edge Directional Couplers | 3 | 3 | 2x2: 3 |
| Defect Cavities | 6 | 6 | 1x1: 6 |
| Edge Couplers | 6 | 6 | 1x1: 4, 2x1: 1, 3x1: 1 |
| Focusing Lattice Grating Couplers | 5 | 5 | 1x0: 4, 2x2: 1 |
| Free Propagation Slab Star Couplers | 5 | 5 | 1x4: 2, 2x4: 1, 2x5: 1, 3x4: 1 |
| Hierarchical Material Splitters | 5 | 5 | 1x2: 4, 1x4: 1 |
| Linear Tapered Grating Couplers | 4 | 4 | 1x0: 4 |
| Mmi Splitters Hybrids | 9 | 7 | 1x2: 4, 1x4: 1, 2x2: 3, 2x3: 1 |
| Mode Material Converters | 6 | 6 | 1x1: 6 |
| Mzi Interferometers | 8 | 5 | 1x1: 7, 2x2: 1 |
| Periodic Structured Couplers | 5 | 5 | 2x2: 5 |
| Single Loop Resonators | 6 | 6 | 1x1: 4, 2x2: 2 |
| Waveguide Crossings | 10 | 10 | 2x2: 9, 3x3: 1 |

## Proposed approval wave

This is an evidence-backed proposal for 100 new representation grammars. It does not allocate realizations, poses, renders, or repair trajectories.

| Level | New grammars | Allocation |
|---|---|---|
| L1 | 12 | `missing_primitive_operation_closure` 8; `visible_terminal_port_operations` 4 |
| L2 | 24 | `ported_body_terminal_motifs` 9; `approach_parallel_departure_coupling_motifs` 6; `split_rejoin_and_feedback_motifs` 4; `repeated_media_transition_motifs` 4; `graded_route_bank_motifs` 1 |
| L3 | 32 | `multiport_body_flow_hierarchies` 4; `coupling_systems` 4; `interferometer_systems` 4; `resonator_graphs` 4; `repeated_media_systems` 4; `lattice_defect_systems` 4; `mode_evolution_systems` 4; `fpr_bank_systems` 4 |
| L4 | 32 | `awg_fpr_components` 6; `resonant_and_distributed_filter_components` 6; `multiport_repeated_components` 4; `interferometer_loop_components` 4; `multimode_interface_components` 4; `split_recombine_components` 4; `grating_components` 2; `edge_interface_components` 2 |

Deprioritized:

- `additional_generic_crossings` — L4 already has ten crossing representations, all exact- and D4-distinct.
- `additional_plain_2x2_directional_couplers` — Conventional, curved, adiabatic, and periodic coupling mechanisms already occupy substantial L4 capacity; the missing value is in curriculum bridges and higher-order systems.
- `additional_single_ring_variants` — Single-loop, structured-loop, and cavity families are populated; new work should change the resonant graph rather than ring dimensions.
- `parameter_only_tooth_pitch_or_count_variants` — Pitch, count, or width changes without a new repetition law are realizations, not new representation grammars.

## Evidence

- `factory/core-v1/freeze.json`
- `factory/core-v1/grammar_catalog.json`
- `metadata/catalog.json`
- `metadata/audit_report.json`
- `metadata/source_reports/l0.json`
- `metadata/source_reports/l1.json`
- `metadata/source_reports/l2.json`
- `metadata/source_reports/l3.json`
- `metadata/source_reports/l4.json`
- `data/l0/train-00000-of-00001.parquet`
- `data/l1/train-00000-of-00001.parquet`
- `data/l2/train-00000-of-00001.parquet`
- `data/l3/train-00000-of-00001.parquet`
- `data/l4/train-00000-of-00001.parquet`

Generated deterministically by `python scripts/audit_coverage.py --root .`.
