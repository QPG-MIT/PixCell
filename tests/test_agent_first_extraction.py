"""Tests for the agent-first extraction primitives (keyless: no VLM API calls).

See the design notes (kept with the lab record)
"""
import io
from pathlib import Path

import fitz
import pytest
from PIL import Image

from homi import paper_processing as pp


def _make_synthetic_pdf(path: Path) -> None:
    """3-page PDF: p1 embedded raster, p2 vector-heavy figure, p3 text only."""
    doc = fitz.open()
    # p1: one embedded raster image
    p1 = doc.new_page(width=300, height=300)
    buf = io.BytesIO()
    Image.new("RGB", (80, 80), (10, 10, 10)).save(buf, format="PNG")
    p1.insert_image(fitz.Rect(20, 20, 100, 100), stream=buf.getvalue())
    # p2: 25 vector rectangles (a drawn figure), no embedded image
    p2 = doc.new_page(width=300, height=300)
    for i in range(25):
        p2.draw_rect(fitz.Rect(10 + i, 10 + i, 40 + i, 40 + i), color=(0, 0, 1))
    # p3: text only
    p3 = doc.new_page(width=300, height=300)
    p3.insert_text((20, 40), "just prose, no figure here")
    doc.save(str(path))
    doc.close()


def test_analyze_pdf_figures_flags_vector_and_embedded(tmp_path):
    pdf = tmp_path / "syn.pdf"
    _make_synthetic_pdf(pdf)

    report = pp.analyze_pdf_figures(str(pdf))

    assert report["total_pages"] == 3
    by_num = {p["page_num"]: p for p in report["pages"]}
    # p1 has an embedded image
    assert by_num[1]["embedded_images"] == 1
    assert by_num[1]["likely_figure"] is True
    # p2 is vector-heavy, zero embedded, still flagged
    assert by_num[2]["embedded_images"] == 0
    assert by_num[2]["vector_draw_ops"] >= 20
    assert by_num[2]["likely_figure"] is True
    # p3 is text only
    assert by_num[3]["likely_figure"] is False
    assert report["recommend_render"] == [1, 2]


def test_crop_region_crops_and_clamps(tmp_path):
    src = tmp_path / "page.png"
    Image.new("RGB", (100, 100), (255, 255, 255)).save(src)
    out = tmp_path / "crop.png"

    res = pp.crop_region(str(src), {"x1": 10, "y1": 10, "x2": 60, "y2": 60}, str(out))

    assert Path(res["output_path"]).exists()
    assert res["cropped_size"] == {"width": 50, "height": 50}
    assert Image.open(out).size == (50, 50)


def test_crop_region_clamps_to_bounds(tmp_path):
    src = tmp_path / "page.png"
    Image.new("RGB", (100, 100), (255, 255, 255)).save(src)
    out = tmp_path / "crop.png"
    # bbox exceeds image; pad pushes further — must clamp to 0..100
    res = pp.crop_region(str(src), {"x1": 80, "y1": 80, "x2": 200, "y2": 200}, str(out), pad_frac=0.5)
    b = res["bbox_applied"]
    assert b["x2"] == 100 and b["y2"] == 100 and b["x1"] >= 0 and b["y1"] >= 0


def test_crop_region_rejects_degenerate_bbox(tmp_path):
    src = tmp_path / "page.png"
    Image.new("RGB", (100, 100), (255, 255, 255)).save(src)
    with pytest.raises(ValueError):
        pp.crop_region(str(src), {"x1": 50, "y1": 50, "x2": 50, "y2": 10}, str(tmp_path / "x.png"))


def test_crop_region_rejects_out_of_bounds_bbox(tmp_path):
    src = tmp_path / "page.png"
    Image.new("RGB", (100, 100), (255, 255, 255)).save(src)
    # box entirely to the RIGHT of the image (passes pre-clamp check, reverses after clamp)
    with pytest.raises(ValueError):
        pp.crop_region(str(src), {"x1": 150, "y1": 10, "x2": 200, "y2": 60}, str(tmp_path / "r.png"))
    # box entirely BELOW the image
    with pytest.raises(ValueError):
        pp.crop_region(str(src), {"x1": 10, "y1": 150, "x2": 60, "y2": 200}, str(tmp_path / "b.png"))


def test_mj_server_advertises_keyless_tools_only():
    from gg.servers.mj_server import MJServer

    names = {t.name for t in MJServer().get_tools()}

    # new keyless tools present
    assert "analyze_pdf_figures" in names
    assert "crop_region" in names
    # retired VLM perception tools gone
    for gone in [
        "score_images", "select_best_image",
        "extract_figure_from_page", "extract_subfigure",
        "extract_footprint_from_paper",
    ]:
        assert gone not in names, f"{gone} should be retired"
    # Gemini B&W generation kept (agent can't generate rasters)
    assert "generate_bw_variants" in names
    assert "refine_bw_image" in names


def test_build_extractor_brief_contains_key_instructions(tmp_path):
    from homi import dispatch

    brief = dispatch.build_extractor_brief("/x/paper.pdf", str(tmp_path), hint="ring in Fig 2")
    assert "/x/paper.pdf" in brief
    assert str(tmp_path) in brief
    assert "ring in Fig 2" in brief
    low = brief.lower()
    # instructs the keyless render->look->crop loop, not API scoring
    assert "analyze_pdf_figures" in low or "render" in low
    assert "crop_region" in low
    assert "score_images" not in low  # no crutch


def test_dispatch_dry_run_returns_command(tmp_path, monkeypatch):
    from homi import dispatch

    monkeypatch.setattr(dispatch.shutil, "which", lambda n: "/usr/bin/" + n)
    monkeypatch.setenv("TMUX", "/tmp/tmux-x")
    res = dispatch.dispatch_extractor_agent("/x/paper.pdf", str(tmp_path), dry_run=True)
    assert res["status"] == "planned"
    assert res["backend"] == "anu-pane"
    # placement is a run-owned tmux session, never `pane spawn` beside the caller
    assert res["command"][:2] == ["tmux", "new-session"]
    assert res["launch"]  # the worker CLI launch line rides separately


def test_dispatch_dry_run_falls_back_to_claude_cli(tmp_path, monkeypatch):
    from homi import dispatch

    # no tmux -> not anu-pane; claude present -> claude-cli
    monkeypatch.setattr(dispatch.shutil, "which", lambda n: "/usr/bin/claude" if n == "claude" else None)
    monkeypatch.delenv("TMUX", raising=False)
    res = dispatch.dispatch_extractor_agent("/x/paper.pdf", str(tmp_path), dry_run=True)
    assert res["backend"] == "claude-cli"
    assert res["command"][:2] == ["claude", "-p"]


def test_cli_extract_dispatches_to_agent(tmp_path, monkeypatch):
    import argparse

    import homi.cli as cli

    called = {}

    def fake_dispatch(pdf_path, output_dir, hint=None, **kw):
        called.update(pdf=pdf_path, out=output_dir, hint=hint)
        return {"status": "ok", "backend": "claude-cli", "command": []}

    # cmd_extract does `from homi import dispatch` then dispatch.dispatch_extractor_agent(...)
    monkeypatch.setattr("homi.dispatch.dispatch_extractor_agent", fake_dispatch)

    pdf = tmp_path / "p.pdf"
    d = fitz.open(); d.new_page(); d.save(str(pdf)); d.close()

    ns = argparse.Namespace(input=pdf, output=(tmp_path / "out"), device="ring resonator", num_variants=5)
    rc = cli.cmd_extract(ns)

    assert called["pdf"] == str(pdf.resolve())
    assert called["hint"] == "ring resonator"
    assert rc in (0, None)


def test_cli_extract_image_input_is_agent_first(tmp_path, monkeypatch):
    """Direct image inputs also dispatch an agent (no in-process Gemini path)."""
    import argparse

    import homi.cli as cli

    called = {}

    def fake_dispatch(input_path, output_dir, hint=None, **kw):
        called.update(input=input_path, out=output_dir, kind=kw.get("input_kind"))
        return {"status": "ok", "backend": "claude-cli", "command": [],
                "artifacts": {"device_bw.png": True, "footprint.json": True}}

    monkeypatch.setattr("homi.dispatch.dispatch_extractor_agent", fake_dispatch)

    img = tmp_path / "device.png"
    Image.new("L", (10, 10), 255).save(img)

    ns = argparse.Namespace(input=img, output=(tmp_path / "out"), device=None, num_variants=5)
    rc = cli.cmd_extract(ns)

    assert called["input"] == str(img.resolve())
    assert called["kind"] == "image"
    assert rc in (0, None)
