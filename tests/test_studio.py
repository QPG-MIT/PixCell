"""PixCell studio — the chat-first surface must stay a valid marimo app."""

import subprocess
import sys
from pathlib import Path


def test_studio_app_passes_marimo_check():
    import homi

    app = Path(homi.__file__).parent / "studio_app.py"
    marimo = Path(sys.executable).parent / "marimo"
    proc = subprocess.run(
        [str(marimo), "check", str(app)], capture_output=True, text=True, timeout=120
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_studio_uses_shared_widgets_and_gate_math():
    import homi

    text = (Path(homi.__file__).parent / "studio_app.py").read_text()
    assert "from homi.workbench import" in text          # shared table widgets
    assert "recompute_metrics" in text                    # fidelity = the gate's own code
    assert "_headless_turn" in text                       # headless conductor turns
    assert 'backend="headless"' in text                   # ride the workspace pool
    assert "mo.ui.tabs(" not in text                      # UI containers clone children


def test_studio_watch_is_gated_and_reset_needs_a_device():
    """The 3s watch must not wipe in-progress play (mo.state gate, never
    mo.stop — stop cancels descendants and blanks the page), and the
    exploration reset only exists once a gate-verified device is loaded."""
    import homi

    text = (Path(homi.__file__).parent / "studio_app.py").read_text()
    assert "mo.state(" in text                            # tick → downstream only on disk change
    assert "mo.stop(" not in text                         # blanks descendants' output
    assert 'if device and device["script"] else None' in text  # reset gated on a device
    assert "run_button" in text
