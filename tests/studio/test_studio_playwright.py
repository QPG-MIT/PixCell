"""Sec. 7.4 regression suite: the studio's released-front-door claims,
verified against a live (sandboxed, headless-mode) studio in a browser.

Each test pins one claim from the paper's studio section — if one breaks,
the paper's description of the released system is wrong until it's fixed.
"""

import pytest

from conftest import (
    FIXTURE, MINIMAL_PDF, deep_text, seed_inflight_project, seed_verified_project,
)

# The seeded-project tests prefer the lab's devtest7 and fall back to the
# TRACKED example_mmi_splitter, so fresh clones run them too.
needs_devtest7 = pytest.mark.skipif(
    not (FIXTURE / "output" / "best.py").exists(),
    reason="no gate-verified fixture project available",
)


# the light table paints its readout on canvas; the widget mirrors it as
# data attributes on its (shadow-DOM) host — walk every shadow root to read it
READ_TABLE_DATA = """() => {
  function* all(root) {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
    let n;
    while ((n = w.nextNode())) { yield n; if (n.shadowRoot) yield* all(n.shadowRoot); }
  }
  for (const n of all(document.body))
    if (n.dataset && n.dataset.iou !== undefined)
      return {iou: n.dataset.iou, gateIou: n.dataset.gateIou, fits: n.dataset.fits};
  return null;
}"""


def _settle(page, url, needle="message the agent", timeout_s=90):
    """Load the studio and wait until `needle` appears in the deep text —
    a cold sandbox server imports gdsfactory and executes the device script
    on first render, which takes far longer than any fixed wait."""
    page.goto(url, wait_until="networkidle", timeout=60000)
    for _ in range(timeout_s):
        if needle in deep_text(page):
            page.wait_for_timeout(1500)  # let sibling cells finish
            return
        page.wait_for_timeout(1000)
    pytest.fail(f"studio never rendered {needle!r} within {timeout_s}s")


class TestEmptyStudio:
    """First contact: no projects at all."""

    def test_loads_clean_with_explainer(self, studio_factory, page):
        srv = studio_factory()
        _settle(page, srv.url)
        text = deep_text(page)
        assert "PixCell" in text
        assert "An internal error occurred" not in text
        # the chat empty-state explains the whole loop
        assert "drop a PDF or a sketch" in text
        # the table's empty state points at the chat
        assert "Nothing on the table yet" in text

    def test_chat_upload_reaches_conductor(self, studio_factory, page):
        """THE headline interaction: a PDF dropped into the chat must land
        in projects/ and be announced to the conductor. Regression for the
        marimo attachments->parts migration silently dropping every upload."""
        srv = studio_factory()
        _settle(page, srv.url)
        pdf = srv.projects.parent / "tiny.pdf"
        pdf.write_bytes(MINIMAL_PDF)
        with page.expect_file_chooser() as fc:
            page.locator(
                'button[aria-label="Attach file"], button:has(svg.lucide-paperclip)'
            ).first.click()
        fc.value.set_files(str(pdf))
        page.wait_for_timeout(1000)
        box = page.locator(".cm-content").first
        box.click()
        box.type("recreate this")
        page.keyboard.press("Enter")
        # condition-based, not a fixed sleep: under full-suite load (several
        # marimo servers + chromium) a 6s window flakes while the turn is
        # still round-tripping through the shim
        for _ in range(30):
            if "fake-conductor reply" in deep_text(page):
                break
            page.wait_for_timeout(1000)
        # the upload landed as a project input
        assert (srv.projects / "tiny" / "paper.pdf").read_bytes() == MINIMAL_PDF
        # the conductor was told exactly where
        prompt = srv.capture.read_text()
        assert "saved to" in prompt and "tiny/paper.pdf" in prompt
        # and the (fake) reply reached the chat panel
        assert "fake-conductor reply" in deep_text(page)


class TestPreflight:
    """The masthead warns — with the exact next step — when the agent CLI
    is missing, instead of failing later with a traceback."""

    def test_no_agent_cli_banner(self, studio_factory, page):
        srv = studio_factory(fake_claude=False)
        _settle(page, srv.url)
        text = deep_text(page)
        assert "no agent CLI on PATH" in text
        assert "claude.com/claude-code" in text
        # the studio still works as an instrument
        assert "Nothing on the table yet" in text


@needs_devtest7
class TestVerifiedDevice:
    """A gate-verified program on the light table."""

    def test_table_knobs_gate_iou(self, studio_factory, page):
        srv = studio_factory(seed=seed_verified_project)
        _settle(page, srv.url, needle="reset — back to the verified GDS", timeout_s=120)
        text = deep_text(page)
        assert "An internal error occurred" not in text
        # knobs are the program's own named parameters
        assert "reset — back to the verified GDS" in text
        # stage strip reads from disk: input through gate must be ticked
        strip = page.evaluate(
            """() => Array.from(document.querySelectorAll('.studio-stages .st'))
                 .map(n => n.className.includes('done') ? '+' + n.innerText.trim()
                                                        : '-' + n.innerText.trim())"""
        )
        done = {s[1:].replace("✓", "").strip().lower()
                for s in strip if s.startswith("+")}
        assert {"input", "silhouette", "gds", "gate"} <= done

    def test_live_iou_matches_gate_at_defaults(self, studio_factory, page):
        """At the program's own values the live IoU must equal the recorded
        gate IoU — the displayed number is the record's, never a cached claim."""
        srv = studio_factory(seed=seed_verified_project)
        _settle(page, srv.url, needle="reset — back to the verified GDS", timeout_s=120)
        nums = page.evaluate(READ_TABLE_DATA)
        assert nums and nums["iou"] and nums["gateIou"], f"no readout: {nums}"
        assert abs(float(nums["iou"]) - float(nums["gateIou"])) <= 0.005


@needs_devtest7
class TestInFlightProject:
    """A dropped input is visible while the workers run (Sec. 7.4: the
    stage monitor ticks exactly when artifacts exist on disk)."""

    def test_inflight_visible_with_stage_ticks(self, studio_factory, page):
        srv = studio_factory(seed=seed_inflight_project)
        _settle(page, srv.url, needle="workers running", timeout_s=120)
        text = deep_text(page)
        assert "inflight_smoke · in progress" in text
        assert "workers running" in text
        strip = page.evaluate(
            """() => Array.from(document.querySelectorAll('.studio-stages .st'))
                 .map(n => n.className.includes('done') ? '+' + n.innerText.trim()
                                                        : '-' + n.innerText.trim())"""
        )
        done = {s[1:].replace("✓", "").strip().lower()
                for s in strip if s.startswith("+")}
        assert {"input", "silhouette"} <= done
        assert "gds" not in done


class TestDrawMode:
    """Sketch + typed footprint = a complete task pair (Sec. 7.4)."""

    def test_draw_save_writes_task_pair(self, studio_factory, page):
        srv = studio_factory()
        _settle(page, srv.url)
        page.get_by_text("Draw", exact=True).first.click()
        canvas = page.locator("canvas").last
        canvas.wait_for(state="visible", timeout=60000)
        box = canvas.bounding_box()
        assert box, "ink canvas not visible in Draw mode"
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.mouse.move(x - 80, y)
        page.mouse.down()
        for dx in range(-80, 81, 8):
            page.mouse.move(x + dx, y)
        page.mouse.up()
        page.wait_for_timeout(1000)
        page.get_by_text("Save sketch as project").first.click()
        page.wait_for_timeout(3000)
        proj = srv.projects / "sketch1"
        assert (proj / "device_bw.png").exists()
        import json
        fp = json.loads((proj / "footprint.json").read_text())
        assert fp["footprint_um"] == [20.0, 5.0]
        # and the save note tells the human the exact next step
        assert "recreate projects/sketch1" in deep_text(page)
