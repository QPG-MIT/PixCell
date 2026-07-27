"""Generate Figure 10 and Table II from the frozen retargeting evidence.

The compact inputs in ``fig_retargeting_assets`` are derived from the tracked
campaign record in QPG-MIT/PixCell-running. Their manifest records both the
source commit and content hashes so the paper repository can rebuild these
assets without duplicating the complete simulation campaign.

Run from the repository root:
    python arxiv/scripts/make_fig_pdk_swap.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_retargeting_assets")
MANIFEST = ASSET_DIR / "manifest.json"
FIGURE_DIR = REPO / "arxiv" / "figures"
TABLE_PATH = REPO / "arxiv" / "table_retargeting.tex"

INK = "#17191c"
SOFT_INK = "#555a60"
PASS = "#246b5a"
PASS_FILL = "#e2eee9"
MISS = "#7e858a"
MISS_FILL = "#f1f2f2"
MISS_EDGE = "#cfd2d4"

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": [
            "Iowan Old Style",
            "STIX Two Text",
            "STIXGeneral",
            "Times New Roman",
        ],
        "mathtext.fontset": "stix",
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": "white",
        "savefig.bbox": None,
    }
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verified_json(specification: dict) -> dict:
    path = ASSET_DIR / specification["asset"]
    actual = _sha256(path)
    expected = specification["sha256"]
    if actual != expected:
        raise ValueError(
            f"Hash mismatch for {path}: expected {expected}, got {actual}."
        )
    return json.loads(path.read_text())


def _load_inputs() -> tuple[dict, dict]:
    manifest = json.loads(MANIFEST.read_text())
    cross_stack = _verified_json(manifest["cross_stack"])
    outcomes = _verified_json(manifest["fixed_representation"])
    return cross_stack, outcomes


def _validate_cross_stack(data: dict) -> None:
    stacks = [stack["id"] for stack in data["stack_order"]]
    target = float(data["target_nm"])
    tolerance = float(data["tolerance_rel"])
    opus = data["opus48m"]["design_stack"]
    gpt = data["gpt55x"]["design_stack"]

    if set(opus) != set(stacks) or set(gpt) != set(stacks):
        raise ValueError("Cross-stack design rows do not match the stack contract.")

    differences = []
    for design in stacks:
        if set(opus[design]) != set(stacks) or set(gpt[design]) != set(stacks):
            raise ValueError(f"Cross-stack columns are incomplete for {design}.")
        for evaluated in stacks:
            value = float(opus[design][evaluated])
            passes = abs(value - target) / target <= tolerance
            expected = design == evaluated
            if passes != expected:
                raise ValueError(
                    f"Unexpected transfer verdict for {design} -> {evaluated}: "
                    f"{value:.6f} nm."
                )
            differences.append(abs(value - float(gpt[design][evaluated])))

    if max(differences) >= 0.002:
        raise ValueError(
            "The GPT-5.5 comparison differs from the Opus matrix by at least "
            "0.002 nm."
        )


def _summarize_outcomes(data: dict) -> dict[str, int]:
    stacks = data["stack_order"]
    models = data["models"]
    if len(stacks) != 3 or len(models) != 2:
        raise ValueError("Table II requires three stacks and two model groups.")

    device_order = [device["name"] for device in models[0]["devices"]]
    if len(device_order) != 5:
        raise ValueError("Table II requires five devices.")

    summary = {
        "R_passes": 0,
        "L_passes": 0,
        "paired_agreements": 0,
        "R_only_passes": 0,
        "L_only_passes": 0,
    }
    for model in models:
        if [device["name"] for device in model["devices"]] != device_order:
            raise ValueError("Model groups use different device ordering.")
        for device in model["devices"]:
            for representation in ("R", "L"):
                values = device[representation]
                if len(values) != len(stacks) or not all(
                    isinstance(value, bool) for value in values
                ):
                    raise ValueError(
                        f"Invalid {representation} verdicts for {device['name']}."
                    )
                summary[f"{representation}_passes"] += sum(values)
            for reconstructed, library in zip(device["R"], device["L"]):
                summary["paired_agreements"] += reconstructed == library
                summary["R_only_passes"] += reconstructed and not library
                summary["L_only_passes"] += library and not reconstructed
    return summary


def _validate_outcomes(data: dict) -> None:
    summary = _summarize_outcomes(data)
    expected = data["expected_summary"]
    if summary != expected:
        raise ValueError(
            f"Table II summary does not reconcile: expected {expected}, got {summary}."
        )

    source = data["source"]
    expected_cells = (
        len(data["models"])
        * len(data["models"][0]["devices"])
        * 2
        * len(data["stack_order"])
    )
    if int(source["source_file_count"]) != expected_cells:
        raise ValueError("The Table II source-file count does not match its cells.")


def _render_cross_stack(data: dict) -> None:
    stacks = [stack["id"] for stack in data["stack_order"]]
    labels = {stack["id"]: stack["label"] for stack in data["stack_order"]}
    target = float(data["target_nm"])
    tolerance = float(data["tolerance_rel"])
    matrix = data["opus48m"]["design_stack"]

    # Match the white-page Iowan/STIX hierarchy used by Figures 1, 2, 5,
    # 6, 8, and 9.  The matrix is deliberately rectangular: forcing square
    # cells left a large unused gutter in a single-column figure and made the
    # visible content appear right-aligned.
    figure = plt.figure(figsize=(3.42, 2.36), facecolor="white")
    axes = figure.add_axes([0.340, 0.225, 0.640, 0.605])

    for row, design in enumerate(stacks):
        for column, evaluated in enumerate(stacks):
            value = float(matrix[design][evaluated])
            passes = abs(value - target) / target <= tolerance
            inset = 0.035
            axes.add_patch(
                Rectangle(
                    (column + inset, row + inset),
                    1 - 2 * inset,
                    1 - 2 * inset,
                    facecolor=PASS_FILL if passes else MISS_FILL,
                    edgecolor=PASS if passes else MISS_EDGE,
                    linewidth=1.05 if passes else 0.55,
                )
            )
            axes.text(
                column + 0.5,
                row + 0.5,
                f"{value:.3f}",
                ha="center",
                va="center",
                color=INK,
                fontsize=9.2,
                fontweight="semibold" if passes else "normal",
            )

    axes.set_xlim(0, len(stacks))
    axes.set_ylim(len(stacks), 0)
    axes.set_xticks([index + 0.5 for index in range(len(stacks))])
    axes.set_yticks([index + 0.5 for index in range(len(stacks))])
    axes.set_xticklabels(
        [labels[stack].rsplit(" ", 1)[0] + "\n" + labels[stack].rsplit(" ", 1)[1]
         for stack in stacks],
        fontsize=8.0,
        color=INK,
        linespacing=0.98,
    )
    axes.set_yticklabels(
        [labels[stack] for stack in stacks],
        fontsize=8.0,
        color=INK,
    )
    axes.tick_params(axis="x", length=0, pad=4.2)
    axes.tick_params(axis="y", length=0, pad=5.0)
    axes.set_xlabel("Evaluated stack", fontsize=8.4, color=INK, labelpad=4.2)
    for spine in axes.spines.values():
        spine.set_visible(False)

    figure.text(
        0.004,
        0.955,
        "Analytic FSR (nm)",
        ha="left",
        va="center",
        fontsize=10.2,
        color=INK,
    )
    figure.text(
        0.98,
        0.955,
        f"target {target:.2f} ± {100 * tolerance:.0f}%",
        ha="right",
        va="center",
        fontsize=8.0,
        color=SOFT_INK,
    )
    figure.add_artist(
        Line2D(
            [0.004, 0.980],
            [0.905, 0.905],
            transform=figure.transFigure,
            color=INK,
            linewidth=0.68,
        )
    )
    figure.text(
        0.004,
        0.825,
        "Geometry tuned for",
        ha="left",
        va="center",
        fontsize=8.4,
        color=INK,
    )

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = FIGURE_DIR / "fig_cross_matrix.pdf"
    png_path = FIGURE_DIR / "fig_cross_matrix.png"
    figure.savefig(pdf_path, dpi=600, facecolor="white", bbox_inches=None)
    figure.savefig(png_path, dpi=300, facecolor="white", bbox_inches=None)
    plt.close(figure)
    print(f"wrote {pdf_path}")
    print(f"wrote {png_path}")


def _table_mark(passes: bool) -> str:
    return r"\retargetpass" if passes else r"\retargetmiss"


def _render_table(data: dict) -> None:
    models = data["models"]
    stacks = data["stack_order"]
    labels = data["stack_labels"]
    by_model = {
        model["id"]: {device["name"]: device for device in model["devices"]}
        for model in models
    }
    device_order = [device["name"] for device in models[0]["devices"]]

    rows = []
    for index, device_name in enumerate(device_order):
        for representation in ("R", "L"):
            values = []
            for model in models:
                values.extend(
                    _table_mark(value)
                    for value in by_model[model["id"]][device_name][representation]
                )
            name = device_name if representation == "R" else ""
            rows.append(
                f"{name:<7} & {representation} & "
                + " & ".join(values)
                + r" \\"
            )
        if index < len(device_order) - 1:
            rows.append(r"\addlinespace[0.12em]")

    totals = {
        model["id"]: {
            representation: sum(
                value
                for device in model["devices"]
                for value in device[representation]
            )
            for representation in ("R", "L")
        }
        for model in models
    }
    total_denominator = len(device_order) * len(stacks)

    model_headers = " & ".join(
        rf"\multicolumn{{3}}{{c}}{{{model['label']}}}" for model in models
    )
    stack_headers = " & ".join(
        labels[stack] for _model in models for stack in stacks
    )
    total_rows = [
        (
            r"Total passes & R & "
            + " & ".join(
                rf"\multicolumn{{3}}{{c}}{{"
                f"{totals[model['id']]['R']}/{total_denominator}"
                r"}"
                for model in models
            )
            + r" \\"
        ),
        (
            r"             & L & "
            + " & ".join(
                rf"\multicolumn{{3}}{{c}}{{"
                f"{totals[model['id']]['L']}/{total_denominator}"
                r"}"
                for model in models
            )
            + r" \\"
        ),
    ]

    table = "\n".join(
        [
            r"\begin{table}[!b]",
            r"\caption{\textbf{Fixed-representation retargeting outcomes.} "
            r"R: reconstructed primitives program; L: library PCell. Columns "
            r"are 220-nm SOI, 400-nm SiN, and 400-nm TFLN. Filled/open markers "
            r"denote pass/observed miss for the tier-0 figure-of-merit plus "
            r"footprint gate.}",
            r"\label{tab:twoarm}",
            r"\begingroup",
            r"\newcommand{\retargetpass}{\textcolor[HTML]{246B5A}{"
            r"\raisebox{0.08ex}{\scalebox{1.05}{$\bullet$}}}}",
            r"\newcommand{\retargetmiss}{\textcolor[HTML]{7E858A}{"
            r"\raisebox{0.08ex}{\scalebox{1.05}{$\circ$}}}}",
            r"\footnotesize",
            r"\setlength{\tabcolsep}{3.35pt}",
            r"\renewcommand{\arraystretch}{1.06}",
            r"\begin{ruledtabular}",
            r"\begin{tabular}{@{}llccc@{\hspace{3.5pt}}ccc@{}}",
            f"& & {model_headers} \\\\",
            f"Device & Rep. & {stack_headers} \\\\",
            r"\colrule",
            *rows,
            r"\colrule",
            *total_rows,
            r"\end{tabular}",
            r"\end{ruledtabular}",
            r"\endgroup",
            r"\end{table}",
            "",
        ]
    )
    TABLE_PATH.write_text(table)
    print(f"wrote {TABLE_PATH}")


def main() -> None:
    cross_stack, outcomes = _load_inputs()
    _validate_cross_stack(cross_stack)
    _validate_outcomes(outcomes)
    _render_cross_stack(cross_stack)
    _render_table(outcomes)


if __name__ == "__main__":
    main()
