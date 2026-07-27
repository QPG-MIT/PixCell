"""Fetch the completed FDTD S-matrix run and overlay it on the analytic tier.

Produces: data/agents/pdk_swap/output/smatrix_result.json and
paper/presentation/pdk_swap_proof/paper/figures/fig_smatrix_fdtd.{png,pdf}

Run from repo root after the task succeeds:
  .venv/bin/python data/agents/pdk_swap/smatrix_fetch.py
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tidy3d import web  # noqa: E402
from tidy3d.constants import C_0  # noqa: E402

from homi.spec_optimization import spectrum  # noqa: E402

TASK_FILE = ROOT / "data/agents/pdk_swap/output/smatrix_task.txt"
SCRIPT = ROOT / "data/agents/pdk_swap/output/optimize/soi220/mzi_soi220.py"
STACK = json.loads((ROOT / "data/agents/pdk_swap/stacks/soi220.json").read_text())
OUT_JSON = ROOT / "data/agents/pdk_swap/output/smatrix_result.json"
FIG_DIR = ROOT / "paper/presentation/pdk_swap_proof/paper/figures"


def fringe_spacing_nm(wl_nm, t):
    """Dominant fringe period via autocorrelation (robust to noise/envelope)."""
    import numpy as np

    wl = np.asarray(wl_nm)
    tt = np.asarray(t)
    wlu = np.linspace(wl[0], wl[-1], 4001)
    tu = np.interp(wlu, wl, tt)
    sig = tu - np.polyval(np.polyfit(wlu, tu, 3), wlu)
    ac = np.correlate(sig, sig, mode="full")[len(sig) - 1:]
    maxima = [i for i in range(6, len(ac) - 1) if ac[i] >= ac[i - 1] and ac[i] >= ac[i + 1]]
    if not maxima:
        return None, []
    return float(maxima[0] * (wlu[1] - wlu[0])), maxima


def main() -> None:
    task_id = TASK_FILE.read_text().strip()
    data = web.load(task_id, path=str(ROOT / "data/agents/pdk_swap/output/smatrix_data.hdf5"))
    amps = data["output_modes"].amps.sel(direction="+", mode_index=0)
    freqs = amps.f.values
    wl_nm = [C_0 / f * 1000 for f in freqs]  # um -> nm
    t_fdtd = [float(abs(a)) ** 2 for a in amps.values]
    order = sorted(range(len(wl_nm)), key=lambda i: wl_nm[i])
    wl_nm = [wl_nm[i] for i in order]
    t_fdtd = [t_fdtd[i] for i in order]

    fsr_fdtd, peaks = fringe_spacing_nm(wl_nm, t_fdtd)

    ana = spectrum(SCRIPT, STACK, span_nm=40.0)
    wl_ana = [w * 1000 for w in ana["wavelength_um"]]

    import numpy as _np

    _t = _np.asarray(t_fdtd)
    t_hi, t_lo = float(_np.percentile(_t, 98)), float(_np.percentile(_t, 2))
    er_db_fdtd = float(10 * _np.log10(t_hi / t_lo)) if t_lo > 0 else None
    result = {
        "task_id": task_id,
        "grid": "min_steps_per_wvl=8 (coarse validation grid)",
        "fsr_fdtd_nm": fsr_fdtd,
        "fsr_analytic_nm": ana["fsr_nm"],
        "target_nm": 8.0,
        "er_db_fdtd_p98_p2": round(er_db_fdtd, 2) if er_db_fdtd else None,
        "mean_T_fdtd": round(float(_t.mean()), 4),
        "autocorr_maxima": len(peaks),
        "billed_estimate_flexcredits": 0.98,
        "note": "fringe SPACING is the validated quantity; depth/level differ "
        "by design (analytic tier assumes ideal 50/50 and lossless)",
    }
    OUT_JSON.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

    fig, ax = plt.subplots(figsize=(4.8, 2.6), dpi=200)
    ax.plot(wl_ana, ana["transmission"], color="#0a5c36", lw=1.0,
            label=f"analytic tier (FSR {ana['fsr_nm']:.2f} nm)")
    label = f"FDTD |S21|$^2$ (FSR {fsr_fdtd:.2f} nm)" if fsr_fdtd else "FDTD |S21|$^2$"
    ax.plot(wl_nm, t_fdtd, color="#4464ad", lw=1.2, label=label)
    ax.set_xlabel("wavelength (nm)")
    ax.set_ylabel("T (bar port)")
    ax.set_xlim(1530, 1570)
    ax.legend(fontsize=7, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.savefig(FIG_DIR / "fig_smatrix_fdtd.png", bbox_inches="tight")
    fig.savefig(FIG_DIR / "fig_smatrix_fdtd.pdf", bbox_inches="tight")
    print("figure written")


if __name__ == "__main__":
    main()
