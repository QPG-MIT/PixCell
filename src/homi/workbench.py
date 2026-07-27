"""The device workbench — one designed surface; everything else integrations.

Generates a self-contained marimo notebook per device: the "mask on a light
table" instrument (spec: the design notes (kept with the lab record)
design.md). The notebook imports only marimo/anywidget/gdsfactory/PIL/numpy —
all baked into the anu chat box and present in the repo venv — and embeds
everything else (source, knobs, calibration, provenance) as literals at
generation time. The UI never implements physics: rebuilds exec the device's
own script; fidelity is the same calibrated-raster IoU the gate uses.

Two variants from one generator:
  draw=False  — play-only (chat artifact / read-only exploration)
  draw=True   — local instrument incl. the Draw tab (dispatches a recreation
                worker through the repo's own control plane via `homi generate`)
"""

from __future__ import annotations

import shutil
from pathlib import Path

# --------------------------------------------------------------------------
# The light table: canvas widget. Chrome mask on backlit white, µm scale bar,
# die-boundary footprint frame, target ghost, crosshair readout, zoom/pan.
# --------------------------------------------------------------------------
_WIDGET_STYLE = r"""
/* The canvas is absolutely positioned so it can NEVER drive the wrap's size —
   otherwise canvas-width -> wrap-width -> ResizeObserver -> canvas-width is a
   runaway feedback loop (measured: 8800px wide tables). */
.wb-table-wrap { position: relative; border: 1px solid #DBD9D2;
  border-radius: 2px; overflow: hidden; background: #fff;
  width: 100%; min-width: 0; }
.wb-table-wrap canvas { position: absolute; inset: 0; display: block;
  cursor: crosshair; touch-action: none; }
.wb-readout { position: absolute; right: 10px; bottom: 8px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px;
  color: #3E4348; opacity: 0.8; pointer-events: none; }
.wb-palette { display: flex; gap: 6px; margin: 0 0 6px 0; flex-wrap: wrap;
  align-items: center; position: relative; }
.wb-tool { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10.5px; letter-spacing: 0.05em; text-transform: uppercase;
  padding: 4px 10px; border: 1px solid #DBD9D2; border-radius: 2px;
  background: #fff; color: #3E4348; cursor: pointer; }
.wb-tool.active { border-color: #17191C; color: #17191C; font-weight: 600; }
.wb-tray { position: absolute; top: 30px; left: 0; z-index: 20; background: #fff;
  border: 1px solid #DBD9D2; border-radius: 2px; padding: 10px;
  display: grid; grid-template-columns: repeat(5, 84px); gap: 8px;
  box-shadow: 0 4px 16px rgba(23,25,28,0.08); }
.wb-stencil { display: flex; flex-direction: column; align-items: center; gap: 4px;
  border: 1px solid transparent; border-radius: 2px; padding: 6px 2px;
  background: #fff; cursor: pointer; }
.wb-stencil:hover { border-color: #DBD9D2; }
.wb-stencil svg { display: block; }
.wb-stencil span { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 9px; color: #3E4348; }
.wb-layerchip { width: 18px; height: 18px; border-radius: 2px; border: 1px solid #DBD9D2;
  cursor: pointer; padding: 0; }
.wb-layerchip.active { outline: 2px solid #17191C; outline-offset: 1px; }
"""

# The photonic stencil vocabulary — ported verbatim from the writing engine
# (~/src/aadarwal/writing-data web/src/App.tsx, commit 57ce003): EXACTLY the
# extended catalog's §1 waveguide primitives + §2 basic shapes, under the
# catalog's own names. Nothing device-shaped is ever allowed here — no MMI,
# no Y-branch: composing primitives into a device is the model's job.
# Stretch-to-fit: drag defines the box, the path scales into it.
_PHOTONIC_KINDS_JS = r"""
const PHOTONIC_KINDS = {
  straight:        { vb: [0,0,100,40], d: 'M0 14 H100 V26 H0 Z' },
  bend_euler:      { vb: [0,0,40,40],  d: 'M0 4 A36 36 0 0 1 36 40 L24 40 A24 24 0 0 0 0 16 Z' },
  bend_circular:   { vb: [0,0,40,40],  d: 'M0 2 A38 38 0 0 1 38 40 L28 40 A28 28 0 0 0 0 12 Z' },
  bend_s:          { vb: [0,0,100,40], d: 'M0 4 C55 4 45 28 100 28 L100 36 C45 36 55 12 0 12 Z' },
  taper:           { vb: [0,0,100,40], d: 'M0 6 L100 15 V25 L0 34 Z' },
  coupler_straight:{ vb: [0,0,100,40], d: 'M0 10 H100 V17 H0 Z M0 23 H100 V30 H0 Z' },
  rectangle:       { vb: [0,0,100,40], d: 'M0 0 H100 V40 H0 Z' },
  circle:          { vb: [0,0,40,40],  d: 'M20 2 A18 18 0 1 0 20 38 A18 18 0 1 0 20 2 Z' },
  ring:            { vb: [0,0,40,40],  d: 'M20 2 A18 18 0 1 0 20 38 A18 18 0 1 0 20 2 Z M20 9 A11 11 0 1 1 20 31 A11 11 0 1 1 20 9 Z', evenodd: true },
  cross:           { vb: [0,0,40,40],  d: 'M15 0 H25 V15 H40 V25 H25 V40 H15 V25 H0 V15 H15 Z' },
  triangle:        { vb: [0,0,100,40], d: 'M0 40 L100 40 L100 0 Z' },
  ellipse:         { vb: [0,0,100,40], d: 'M50 2 A48 18 0 1 0 50 38 A48 18 0 1 0 50 2 Z' },
  regular_polygon: { vb: [0,0,40,40],  d: 'M10 3 H30 L40 20 L30 37 H10 L0 20 Z' },
  L:               { vb: [0,0,40,40],  d: 'M0 0 H12 V28 H40 V40 H0 Z' },
};
const LAYER_COLORS = { 1: "#17191C", 2: "#5B7C8D", 3: "#8D6B5B" };
"""

_LIGHT_TABLE_ESM = r"""
const WIDGET_CSS = `__WIDGET_STYLE__`;
__PHOTONIC_KINDS_JS__
function render({ model, el }) {
  el.innerHTML = "";
  const style = document.createElement("style");
  style.textContent = WIDGET_CSS;   // shadow DOM: document CSS does not reach here
  el.appendChild(style);
  const wrap = document.createElement("div");
  wrap.className = "wb-table-wrap";
  const canvas = document.createElement("canvas");
  const readout = document.createElement("div");
  readout.className = "wb-readout";
  readout.textContent = "";
  wrap.appendChild(canvas);
  wrap.appendChild(readout);
  el.appendChild(wrap);

  const ctx = canvas.getContext("2d");
  const DPR = window.devicePixelRatio || 1;
  let W = 0, H = 0;

  // view state (µm-space -> px): scale s, offset (ox, oy)
  let s = 1, ox = 0, oy = 0, userView = false;
  let ghostImg = null;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let develop = reduced ? 1 : 0;   // load-in: the mask develops once
  let raf = null;

  function allPolys() {
    // flat polygons (single-layer callers) + per-layer sets (studio)
    const flat = (model.get("polygons") || []).map((p) => [1, p]);
    const layered = model.get("layer_polygons") || {};
    for (const [l, plist] of Object.entries(layered)) {
      for (const p of plist) flat.push([Number(l), p]);
    }
    return flat;
  }

  function polysBounds(polys, fp) {
    let x0 = 0, y0 = 0, x1 = fp ? fp[0] : 1, y1 = fp ? fp[1] : 1;
    for (const [, poly] of polys) for (const [x, y] of poly) {
      x0 = Math.min(x0, x); y0 = Math.min(y0, y);
      x1 = Math.max(x1, x); y1 = Math.max(y1, y);
    }
    return [x0, y0, x1, y1];
  }

  function fitView() {
    const polys = allPolys();
    const fp = model.get("footprint_um");
    const [x0, y0, x1, y1] = polysBounds(polys, fp);
    const mw = Math.max(x1 - x0, 1e-6), mh = Math.max(y1 - y0, 1e-6);
    const pad = 0.12;
    s = Math.min(W / (mw * (1 + 2 * pad)), H / (mh * (1 + 2 * pad)));
    ox = (W - mw * s) / 2 - x0 * s;
    oy = (H - mh * s) / 2 - y0 * s;
  }

  function niceScaleBar() {
    const targetPx = W / 5;
    const um = targetPx / s;
    const pow = Math.pow(10, Math.floor(Math.log10(um)));
    let step = pow;
    for (const m of [5, 2, 1]) if (um / pow >= m) { step = m * pow; break; }
    return step;
  }

  function toPx(x, y) { return [x * s + ox, H - (y * s + oy)]; }

  function draw() {
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const css = getComputedStyle(el);
    const chrome = css.getPropertyValue("--chrome").trim() || "#17191C";
    const resist = css.getPropertyValue("--resist").trim() || "#C9861B";
    const violation = css.getPropertyValue("--violation").trim() || "#B3362B";
    const hairline = css.getPropertyValue("--hairline").trim() || "#DBD9D2";

    // backlit field: faintest radial glow, like a light table
    const g = ctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, Math.max(W, H) / 1.2);
    g.addColorStop(0, "#FFFFFF");
    g.addColorStop(1, "#F2F1EC");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);

    let targetShown = false;

    // fidelity readout, top-right IN the instrument (never a separate card)
    const iou = model.get("iou");
    const gate = model.get("gate_iou");
    const fits = model.get("fits");
    // canvas paint is invisible to the DOM — mirror the readout as data
    // attributes so tests and assistive tech can see the same numbers
    el.dataset.iou = iou == null ? "" : String(iou);
    el.dataset.gateIou = gate == null ? "" : String(gate);
    el.dataset.fits = fits == null ? "" : String(fits);
    let fy = 16;
    ctx.textAlign = "right";
    if (iou !== null && iou !== undefined) {
      ctx.fillStyle = iou >= 0.85 ? resist : violation;
      ctx.font = "600 15px ui-monospace, SFMono-Regular, Menlo, monospace";
      ctx.fillText("IoU " + iou.toFixed(4), W - 12, fy + 12);
      fy += 18;
      if (gate !== null && gate !== undefined) {
        ctx.font = "12px ui-monospace, SFMono-Regular, Menlo, monospace";
        ctx.fillStyle = "#3E4348";
        ctx.fillText("gate " + gate.toFixed(4), W - 12, fy + 11);
        fy += 16;
      }
    }
    if (fits !== null && fits !== undefined) {
      ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, monospace";
      ctx.fillStyle = fits ? "#3E4348" : violation;
      ctx.fillText(fits ? "within footprint" : "EXCEEDS FOOTPRINT", W - 12, fy + 10);
    }
    ctx.textAlign = "left";

    // target ghost — the silhouette the device is SCORED against, drawn
    // through the calibration transform (same px<->um mapping as the IoU),
    // so it sits exactly under the mask. Red tint + TARGET chip: it must
    // never read as mystery-grey.
    const fp = model.get("footprint_um");
    const calib = model.get("calib");
    if (ghostImg && model.get("show_ghost") && fp) {
      let leftUm = 0, topUm = fp[1], wUm = fp[0], hUm = fp[1];
      if (calib && calib.sx) {
        leftUm = -calib.offx / calib.sx;
        topUm = fp[1] + calib.offy / calib.sy;
        wUm = calib.w / calib.sx;
        hUm = calib.h / calib.sy;
      }
      const [gx, gy] = toPx(leftUm, topUm);
      ctx.globalAlpha = 0.45;
      ctx.drawImage(ghostImg, gx, gy, wUm * s, hUm * s);
      ctx.globalAlpha = 1;
      ctx.fillStyle = violation;
      ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, monospace";
      ctx.fillText("TARGET", 14, 21);
      targetShown = true;
    }

    // die boundary = the footprint budget
    if (fp) {
      const [fx, fy] = toPx(0, fp[1]);
      ctx.strokeStyle = model.get("violation") ? violation : hairline;
      ctx.lineWidth = model.get("violation") ? 1.6 : 1;
      ctx.setLineDash([6, 4]);
      ctx.strokeRect(fx, fy, fp[0] * s, fp[1] * s);
      ctx.setLineDash([]);
    }

    // the mask — layer 1 in chrome; assigned layers in their own colors
    ctx.globalAlpha = develop;
    const layersSeen = new Set();
    for (const [l, poly] of allPolys()) {
      layersSeen.add(l);
      ctx.fillStyle = (l === 1 ? chrome : (LAYER_COLORS[l] || chrome));
      ctx.beginPath();
      poly.forEach(([x, y], i) => {
        const [px, py] = toPx(x, y);
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      });
      ctx.closePath();
      ctx.fill();
    }
    ctx.globalAlpha = 1;

    // layer legend chips, top-left (only when more than one layer is live)
    if (layersSeen.size > 1) {
      let lx = targetShown ? 76 : 14;
      for (const l of [...layersSeen].sort()) {
        ctx.fillStyle = (l === 1 ? chrome : (LAYER_COLORS[l] || chrome));
        ctx.fillRect(lx, 12, 10, 10);
        ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, monospace";
        ctx.fillText(`(${l},0)`, lx + 14, 21);
        lx += 58;
      }
    }

    // µm scale bar, bottom left — drawn at develop progress
    const step = niceScaleBar();
    const bx = 18, by = H - 22, bw = step * s * develop;
    ctx.strokeStyle = chrome;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(bx, by); ctx.lineTo(bx + bw, by);
    ctx.moveTo(bx, by - 4); ctx.lineTo(bx, by + 4);
    ctx.moveTo(bx + bw, by - 4); ctx.lineTo(bx + bw, by + 4);
    ctx.stroke();
    ctx.fillStyle = resist;
    ctx.font = "11px ui-monospace, SFMono-Regular, Menlo, monospace";
    ctx.fillText(step >= 1 ? step + " µm" : (step * 1000) + " nm", bx, by - 8);
  }

  function animate() {
    if (develop < 1) {
      develop = Math.min(1, develop + 0.06);
      draw();
      raf = requestAnimationFrame(animate);
    } else { draw(); }
  }

  function resize() {
    const rect = wrap.getBoundingClientRect();
    if (rect.width < 50) return;  // hidden (inactive tab) — wait for layout
    W = rect.width;
    H = model.get("height") || 460;
    wrap.style.height = H + "px";
    canvas.width = W * DPR; canvas.height = H * DPR;
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
    if (!userView) fitView();
    draw();
  }
  // tab containers report bogus widths during mount — settle passes
  setTimeout(resize, 250);
  setTimeout(resize, 1000);

  // crosshair readout in µm — the instrument speaks in physical units
  canvas.addEventListener("mousemove", (e) => {
    const r = canvas.getBoundingClientRect();
    const x = (e.clientX - r.left - ox) / s;
    const y = (H - (e.clientY - r.top) - oy) / s;
    readout.textContent = x.toFixed(3) + ", " + y.toFixed(3) + " µm";
  });
  canvas.addEventListener("mouseleave", () => { readout.textContent = ""; });

  // zoom to cursor / drag pan / double-click reset
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    userView = true;
    const r = canvas.getBoundingClientRect();
    const mx = e.clientX - r.left, my = H - (e.clientY - r.top);
    const f = Math.exp(-e.deltaY * 0.0015);
    ox = mx - (mx - ox) * f;
    oy = my - (my - oy) * f;
    s *= f;
    draw();
  }, { passive: false });
  let dragging = null;
  canvas.addEventListener("pointerdown", (e) => { dragging = [e.clientX, e.clientY]; });
  window.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    userView = true;
    ox += e.clientX - dragging[0];
    oy -= e.clientY - dragging[1];
    dragging = [e.clientX, e.clientY];
    draw();
  });
  window.addEventListener("pointerup", () => { dragging = null; });
  canvas.addEventListener("dblclick", () => { userView = false; fitView(); draw(); });

  const ghost = model.get("ghost_data_uri");
  if (ghost) {
    // preprocess once: dark pixels -> violation red, white -> transparent
    const raw = new Image();
    raw.onload = () => {
      const off = document.createElement("canvas");
      off.width = raw.width; off.height = raw.height;
      const octx = off.getContext("2d");
      octx.drawImage(raw, 0, 0);
      const id = octx.getImageData(0, 0, off.width, off.height);
      const d = id.data;
      for (let i = 0; i < d.length; i += 4) {
        const dark = d[i] < 245;   // same threshold as the metric
        d[i] = 179; d[i + 1] = 54; d[i + 2] = 43;
        d[i + 3] = dark ? 255 : 0;
      }
      octx.putImageData(id, 0, 0);
      ghostImg = off;
      draw();
    };
    raw.src = ghost;
  }

  model.on("change:polygons", () => { if (!userView) fitView(); draw(); });
  model.on("change:layer_polygons", () => { if (!userView) fitView(); draw(); });
  model.on("change:violation", draw);
  model.on("change:show_ghost", draw);
  model.on("change:iou", draw);
  model.on("change:gate_iou", draw);
  model.on("change:fits", draw);

  const ro = new ResizeObserver(resize);
  ro.observe(wrap);
  resize();
  if (raf) cancelAnimationFrame(raf);
  animate();
}
export default { render };
"""

# --------------------------------------------------------------------------
# The ink surface: Draw mode shares the light table. Pointer strokes on the
# backlit field; the sketch leaves as a PNG data-URI trait.
# --------------------------------------------------------------------------
_INK_TABLE_ESM = r"""
const WIDGET_CSS = `__WIDGET_STYLE__`;
__PHOTONIC_KINDS_JS__
function render({ model, el }) {
  el.innerHTML = "";
  const style = document.createElement("style");
  style.textContent = WIDGET_CSS;   // shadow DOM: document CSS does not reach here
  el.appendChild(style);

  // ---- toolbar: ink · stencil tray · undo. Drawing is BLACK AND WHITE ONLY:
  // the silhouette is the blind-recreation input; layers belong to the built
  // program, assigned per primitive AFTER the gate (never at sketch time). ----
  const bar = document.createElement("div");
  bar.className = "wb-palette";
  el.appendChild(bar);

  let tool = "ink";          // "ink" or a PHOTONIC_KINDS key
  let shapes = [];           // {t:"ink",pts,width} | {t:<kind>, a, b}
  let current = null;        // shape being drawn/placed
  let selected = -1;         // index into shapes
  let action = null;         // null | "draw" | "move" | "resize"
  let grab = null;           // pointer bookkeeping

  const inkBtn = document.createElement("button");
  inkBtn.type = "button"; inkBtn.className = "wb-tool active"; inkBtn.textContent = "ink";
  bar.appendChild(inkBtn);

  const trayBtn = document.createElement("button");
  trayBtn.type = "button"; trayBtn.className = "wb-tool"; trayBtn.textContent = "stencils";
  bar.appendChild(trayBtn);

  const tray = document.createElement("div");
  tray.className = "wb-tray"; tray.style.display = "none";
  for (const [kind, k] of Object.entries(PHOTONIC_KINDS)) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "wb-stencil";
    b.innerHTML = `<svg width="64" height="26" viewBox="${k.vb.join(' ')}" preserveAspectRatio="none">` +
      `<path d="${k.d}" fill="#111" fill-rule="${k.evenodd ? 'evenodd' : 'nonzero'}"/></svg>` +
      `<span>${kind}</span>`;
    b.addEventListener("click", () => {
      tool = kind;
      inkBtn.classList.remove("active");
      trayBtn.classList.add("active");
      trayBtn.textContent = kind;
      tray.style.display = "none";
    });
    tray.appendChild(b);
  }
  bar.appendChild(tray);
  trayBtn.addEventListener("click", () => {
    tray.style.display = tray.style.display === "none" ? "grid" : "none";
  });
  inkBtn.addEventListener("click", () => {
    tool = "ink";
    inkBtn.classList.add("active");
    trayBtn.classList.remove("active");
    trayBtn.textContent = "stencils";
    tray.style.display = "none";
  });

  const undoBtn = document.createElement("button");
  undoBtn.type = "button"; undoBtn.className = "wb-tool"; undoBtn.textContent = "undo";
  undoBtn.addEventListener("click", () => {
    shapes.pop(); selected = -1; draw(); push();
  });
  bar.appendChild(undoBtn);

  // orientation controls — visible only while a stencil shape is selected
  const orientBtns = [];
  function orientBtn(label, fn) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "wb-tool"; b.textContent = label;
    b.style.display = "none";
    b.addEventListener("click", () => {
      if (selected >= 0 && shapes[selected] && shapes[selected].t !== "ink") {
        fn(shapes[selected]); draw(); push();
      }
    });
    bar.appendChild(b); orientBtns.push(b);
  }
  orientBtn("flip ↔", (sh) => { sh.fx = !sh.fx; });
  orientBtn("flip ↕", (sh) => { sh.fy = !sh.fy; });
  orientBtn("rotate", (sh) => { sh.rot = ((sh.rot || 0) + 1) % 4; });

  const wrap = document.createElement("div");
  wrap.className = "wb-table-wrap wb-ink";
  wrap.tabIndex = 0;   // so Delete/Backspace reach us
  const canvas = document.createElement("canvas");
  const hint = document.createElement("div");
  hint.className = "wb-readout";
  hint.textContent = "drag to draw or place — drag direction sets orientation · select a stencil: flip/rotate (h·v·r) · black = material";
  wrap.appendChild(canvas);
  wrap.appendChild(hint);
  el.appendChild(wrap);

  const ctx = canvas.getContext("2d");
  const DPR = window.devicePixelRatio || 1;
  let W = 0, H = 0;

  function bboxOf(sh) {
    if (sh.t === "ink") {
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      for (const [x, y] of sh.pts) {
        x0 = Math.min(x0, x); y0 = Math.min(y0, y);
        x1 = Math.max(x1, x); y1 = Math.max(y1, y);
      }
      const pad = (sh.width || 10) / 2;
      return [x0 - pad, y0 - pad, x1 + pad, y1 + pad];
    }
    return [Math.min(sh.a[0], sh.b[0]), Math.min(sh.a[1], sh.b[1]),
            Math.max(sh.a[0], sh.b[0]), Math.max(sh.a[1], sh.b[1])];
  }
  function hitShape(p) {
    for (let i = shapes.length - 1; i >= 0; i--) {
      const [x0, y0, x1, y1] = bboxOf(shapes[i]);
      if (p[0] >= x0 && p[0] <= x1 && p[1] >= y0 && p[1] <= y1) return i;
    }
    return -1;
  }
  function moveShape(sh, dx, dy) {
    if (sh.t === "ink") { for (const pt of sh.pts) { pt[0] += dx; pt[1] += dy; } }
    else { sh.a[0] += dx; sh.a[1] += dy; sh.b[0] += dx; sh.b[1] += dy; }
  }
  function scaleShape(sh, bbox, sx, sy) {
    const [x0, y0] = bbox;
    if (sh.t === "ink") {
      for (const pt of sh.pts) {
        pt[0] = x0 + (pt[0] - x0) * sx;
        pt[1] = y0 + (pt[1] - y0) * sy;
      }
    } else {
      sh.a = [x0 + (sh.a[0] - x0) * sx, y0 + (sh.a[1] - y0) * sy];
      sh.b = [x0 + (sh.b[0] - x0) * sx, y0 + (sh.b[1] - y0) * sy];
    }
  }

  function drawShape(c, sh, color) {
    const col = color || "#17191C";
    c.fillStyle = col; c.strokeStyle = col;
    if (sh.t === "ink") {
      c.lineWidth = sh.width;
      c.lineCap = "round"; c.lineJoin = "round";
      c.beginPath();
      sh.pts.forEach(([x, y], i) => (i === 0 ? c.moveTo(x, y) : c.lineTo(x, y)));
      c.stroke();
      return;
    }
    const k = PHOTONIC_KINDS[sh.t];
    if (!k) return;
    const [x0, y0, x1, y1] = bboxOf(sh);
    const w = Math.max(x1 - x0, 2), h = Math.max(y1 - y0, 2);
    const [vx, vy, vw, vh] = k.vb;
    // orientation: the drag DIRECTION at placement sets the flips (drawing a
    // bend right-to-left mirrors it, live in the preview); the h/v/r controls
    // on a selection toggle further. bboxOf min/maxes the corners, so the
    // signed a->b order is exactly the information this preserves.
    const flipX = !!sh.fx !== (sh.b[0] < sh.a[0]);
    const flipY = !!sh.fy !== (sh.b[1] < sh.a[1]);
    const rot = sh.rot || 0;
    c.save();
    c.translate(x0, y0);
    c.scale(w, h);                      // unit square = the shape's bbox
    c.translate(0.5, 0.5);
    c.rotate(rot * Math.PI / 2);
    c.scale(flipX ? -1 : 1, flipY ? -1 : 1);
    c.translate(-0.5, -0.5);
    c.scale(1 / (vw - vx), 1 / (vh - vy));
    c.translate(-vx, -vy);
    c.fill(new Path2D(k.d), k.evenodd ? "evenodd" : "nonzero");
    c.restore();
  }

  function draw() {
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.fillStyle = "#FFFFFF";
    ctx.fillRect(0, 0, W, H);
    for (const sh of shapes.concat(current ? [current] : [])) drawShape(ctx, sh);
    if (selected >= 0 && shapes[selected]) {
      const [x0, y0, x1, y1] = bboxOf(shapes[selected]);
      ctx.strokeStyle = "#C9861B";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
      ctx.setLineDash([]);
      ctx.fillStyle = "#C9861B";
      ctx.fillRect(x1 - 4, y1 - 4, 8, 8);   // SE resize handle
    }
    const stencilSel = selected >= 0 && shapes[selected] && shapes[selected].t !== "ink";
    for (const b of orientBtns) b.style.display = stencilSel ? "" : "none";
  }

  function push() {
    const off = document.createElement("canvas");
    off.width = W * 2; off.height = H * 2;
    const octx = off.getContext("2d");
    octx.scale(2, 2);
    octx.fillStyle = "#FFFFFF"; octx.fillRect(0, 0, W, H);
    for (const sh of shapes) drawShape(octx, sh, "#000000");
    model.set("ink_data_uri", shapes.length ? off.toDataURL("image/png") : "");
    model.save_changes();
  }

  function pos(e) {
    const r = canvas.getBoundingClientRect();
    return [e.clientX - r.left, e.clientY - r.top];
  }
  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId);
    wrap.focus();
    const p = pos(e);
    // resize handle of the selection?
    if (selected >= 0 && shapes[selected]) {
      const [, , x1, y1] = bboxOf(shapes[selected]);
      if (Math.abs(p[0] - x1) <= 7 && Math.abs(p[1] - y1) <= 7) {
        action = "resize";
        grab = { p, bbox: bboxOf(shapes[selected]) };
        return;
      }
    }
    // grab an existing shape to MOVE it
    const hit = hitShape(p);
    if (hit >= 0) {
      selected = hit;
      action = "move";
      grab = { p };
      draw();
      return;
    }
    // empty table: draw/place with the current tool
    selected = -1;
    action = "draw";
    const width = model.get("stroke_width") || 10;
    current = tool === "ink"
      ? { t: "ink", pts: [p], width }
      : { t: tool, a: [p[0], p[1]], b: [p[0], p[1]] };
    draw();
  });
  canvas.addEventListener("pointermove", (e) => {
    const p = pos(e);
    if (action === "draw" && current) {
      if (current.t === "ink") current.pts.push(p);
      else current.b = [p[0], p[1]];
      draw();
    } else if (action === "move" && selected >= 0) {
      moveShape(shapes[selected], p[0] - grab.p[0], p[1] - grab.p[1]);
      grab.p = p;
      draw();
    } else if (action === "resize" && selected >= 0) {
      const [x0, y0, x1, y1] = grab.bbox;
      const sx = Math.max((p[0] - x0) / Math.max(x1 - x0, 2), 0.05);
      const sy = Math.max((p[1] - y0) / Math.max(y1 - y0, 2), 0.05);
      scaleShape(shapes[selected], grab.bbox, sx, sy);
      grab.bbox = bboxOf(shapes[selected]);
      grab.p = p;
      draw();
    }
  });
  canvas.addEventListener("pointerup", () => {
    if (action === "draw" && current) {
      shapes.push(current);
      selected = shapes.length - 1;
      current = null;
    }
    if (action) push();
    action = null;
    draw();
  });
  wrap.addEventListener("keydown", (e) => {
    if ((e.key === "Delete" || e.key === "Backspace") && selected >= 0) {
      shapes.splice(selected, 1);
      selected = -1;
      draw(); push();
      e.preventDefault();
    }
    if (selected >= 0 && shapes[selected] && shapes[selected].t !== "ink") {
      const sh = shapes[selected];
      if (e.key === "h") { sh.fx = !sh.fx; draw(); push(); e.preventDefault(); }
      if (e.key === "v") { sh.fy = !sh.fy; draw(); push(); e.preventDefault(); }
      if (e.key === "r") { sh.rot = ((sh.rot || 0) + 1) % 4; draw(); push(); e.preventDefault(); }
    }
  });

  model.on("change:clear_nonce", () => {
    shapes = []; current = null; selected = -1; draw(); push();
  });

  function resize() {
    const rect = wrap.getBoundingClientRect();
    if (rect.width < 50) return;  // hidden (inactive tab) — wait for layout
    W = rect.width;
    H = model.get("height") || 460;
    wrap.style.height = H + "px";
    canvas.width = W * DPR; canvas.height = H * DPR;
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
    draw();
  }
  new ResizeObserver(resize).observe(wrap);
  resize();
  setTimeout(resize, 250);
  setTimeout(resize, 1000);
}
export default { render };
"""

# --------------------------------------------------------------------------
# Design tokens + fascia CSS. Monochrome instrument; amber = measurement only.
# --------------------------------------------------------------------------
_CSS = r"""
<style>
:root {
  --table: #FAFAF8;
  --chrome: #17191C;
  --graphite: #3E4348;
  --hairline: #DBD9D2;
  --resist: #C9861B;
  --violation: #B3362B;
  --pass: #2E7D46;
  --mono: ui-monospace, SFMono-Regular, Menlo, "Cascadia Code", monospace;
}
body, .marimo-app { background: var(--table) !important; }
.wb { color: var(--graphite); font-family: var(--mono); }
.wb-label {
  font-size: 10px; letter-spacing: 0.09em; text-transform: uppercase;
  color: var(--graphite); opacity: 0.75; margin: 0 0 6px 0;
}
.wb-panel {
  border: 1px solid var(--hairline); border-radius: 2px;
  padding: 12px 14px; background: #FFFFFF;
}
.wb-masthead { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap;
  padding: 4px 2px 10px 2px; border-bottom: 1px solid var(--hairline); }
.wb-name { font-family: var(--mono); font-size: 20px; font-weight: 600;
  color: var(--chrome); letter-spacing: 0.01em; }
.wb-class { font-size: 12.5px; color: var(--graphite); opacity: 0.85; max-width: 60ch; }
.wb-badge { font-family: var(--mono); font-size: 11.5px; padding: 3px 8px;
  border: 1px solid var(--resist); color: var(--resist); border-radius: 2px;
  white-space: nowrap; }
.wb-badge.fail { border-color: var(--violation); color: var(--violation); }
.wb-table-wrap { position: relative; border: 1px solid var(--hairline);
  border-radius: 2px; overflow: hidden; background: #fff; }
.wb-table-wrap canvas { display: block; cursor: crosshair; touch-action: none; }
.wb-ink canvas { cursor: crosshair; }
.wb-readout { position: absolute; right: 10px; bottom: 8px;
  font-family: var(--mono); font-size: 11px; color: var(--graphite);
  opacity: 0.8; pointer-events: none; }
.wb-meter { margin: 4px 0 2px 0; }
.wb-meter-track { height: 6px; background: #EEECE6; border-radius: 1px; }
.wb-meter-fill { height: 6px; background: var(--resist); border-radius: 1px;
  transition: width 300ms ease; }
@media (prefers-reduced-motion: reduce) { .wb-meter-fill { transition: none; } }
.wb-num { font-family: var(--mono); font-variant-numeric: tabular-nums; }
.wb-iou { font-family: var(--mono); font-size: 22px; color: var(--resist); }
.wb-iou.fail { color: var(--violation); }
.wb-fit { font-family: var(--mono); font-size: 12px; }
.wb-fit.fail { color: var(--violation); }
.wb-cmd { font-family: var(--mono); font-size: 11.5px; background: #F4F3EE;
  border: 1px solid var(--hairline); border-radius: 2px; padding: 8px 10px;
  overflow-x: auto; white-space: pre; }
.wb-prov dt { font-size: 10px; letter-spacing: 0.09em; text-transform: uppercase;
  opacity: 0.7; margin-top: 8px; }
.wb-prov dd { margin: 2px 0 0 0; font-size: 12.5px; }
input[type="range"] { accent-color: var(--graphite); }
marimo-slider { --slider-thumb: var(--graphite); }
</style>
"""

# --------------------------------------------------------------------------
# The notebook template. Sentinel placeholders (no brace escaping — the JS is
# brace-heavy). Everything __UPPER__ is substituted at generation time.
# --------------------------------------------------------------------------
_TEMPLATE = '''# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "anywidget",
#     "gdsfactory==9.20.7",
#     "pillow",
#     "numpy",
# ]
# ///
# Generated by `homi explore` — the device workbench (mask on a light table).
# Self-contained: rebuilds run the device's own script; fidelity is the same
# calibrated-raster IoU the conductor gate uses. Spec:
# the design notes (kept with the lab record)

import marimo

__generated_with = "0.23.13"
app = marimo.App(width="full")


@app.cell
def _():
    import base64
    import io
    import json
    import tempfile
    from pathlib import Path

    import anywidget
    import marimo as mo
    import numpy as np
    import traitlets
    from PIL import Image, ImageDraw

    return Image, ImageDraw, Path, anywidget, base64, io, json, mo, np, tempfile, traitlets


@app.cell
def _():
    DEVICE_NAME = __DEVICE_NAME__
    SOURCE = __SOURCE__
    MAIN_FUNCTION = __MAIN_FUNCTION__
    PARAMS = __PARAMS__
    FUNCTION_KNOBS = __FUNCTION_KNOBS__
    PROVENANCE = __PROVENANCE__
    FOOTPRINT_UM = __FOOTPRINT_UM__
    CALIB = __CALIB__
    TARGET_DATA_URI = __TARGET_DATA_URI__
    DRAW_MODE = __DRAW_MODE__
    HANDOFF_SCRIPT = __HANDOFF_SCRIPT__
    return (
        CALIB, DEVICE_NAME, DRAW_MODE, FOOTPRINT_UM, FUNCTION_KNOBS,
        HANDOFF_SCRIPT, MAIN_FUNCTION, PARAMS, PROVENANCE, SOURCE, TARGET_DATA_URI,
    )


@app.cell
def _(mo):
    _css = __CSS__
    style = mo.Html(_css)
    style
    return


@app.cell
def _(anywidget, traitlets):
    class LightTable(anywidget.AnyWidget):
        _esm = __LIGHT_TABLE_ESM__
        polygons = traitlets.List([]).tag(sync=True)
        layer_polygons = traitlets.Dict({}).tag(sync=True)
        footprint_um = traitlets.List(allow_none=True).tag(sync=True)
        violation = traitlets.Bool(False).tag(sync=True)
        show_ghost = traitlets.Bool(True).tag(sync=True)
        ghost_data_uri = traitlets.Unicode("").tag(sync=True)
        calib = traitlets.Dict(allow_none=True).tag(sync=True)
        iou = traitlets.Float(allow_none=True).tag(sync=True)
        gate_iou = traitlets.Float(allow_none=True).tag(sync=True)
        fits = traitlets.Bool(allow_none=True).tag(sync=True)
        height = traitlets.Int(460).tag(sync=True)

    class InkTable(anywidget.AnyWidget):
        _esm = __INK_TABLE_ESM__
        ink_data_uri = traitlets.Unicode("").tag(sync=True)
        stroke_width = traitlets.Int(10).tag(sync=True)
        clear_nonce = traitlets.Int(0).tag(sync=True)
        height = traitlets.Int(460).tag(sync=True)

    return InkTable, LightTable


@app.cell
def _(FUNCTION_KNOBS, PARAMS, mo):
    _primary = [p for p in PARAMS if p["name"] in set(FUNCTION_KNOBS)]
    _secondary = [p for p in PARAMS if p["name"] not in set(FUNCTION_KNOBS)]
    if not _primary:
        _primary, _secondary = _secondary, []

    def _slider(p):
        return mo.ui.slider(
            p["min_value"], p["max_value"],
            value=p["default_value"],
            step=p["step"],
            label=p["label"],
            show_value=True,
            full_width=True,
        )

    # mo.ui.dictionary clones its elements — display THESE, read values from
    # the dictionaries (never mix the originals in).
    primary_knobs = mo.ui.dictionary({p["name"]: _slider(p) for p in _primary})
    secondary_knobs = mo.ui.dictionary({p["name"]: _slider(p) for p in _secondary})
    return primary_knobs, secondary_knobs


@app.cell
def _(mo, primary_knobs, secondary_knobs):
    # Display the dictionaries' OWN (cloned, registered) elements — displaying
    # the dictionary object itself renders debug JSON chrome.
    _primary_stack = mo.vstack(list(primary_knobs.elements.values()), gap=0.35)
    if len(secondary_knobs.elements):
        _rest = mo.accordion({
            "Additional parameters":
            mo.vstack(list(secondary_knobs.elements.values()), gap=0.35)
        })
        knob_panel = mo.vstack(
            [mo.Html('<div class="wb-label">Function parameters</div>'),
             _primary_stack, _rest], gap=0.5)
    else:
        knob_panel = mo.vstack(
            [mo.Html('<div class="wb-label">Parameters</div>'), _primary_stack], gap=0.5)
    return (knob_panel,)


@app.cell
def _(FOOTPRINT_UM, MAIN_FUNCTION, SOURCE, Path, primary_knobs, secondary_knobs, tempfile):
    import gdsfactory as gf

    # Recreated programs legitimately use ``Path(__file__)`` for derived
    # records. Executing embedded source has no Python file of its own, so
    # provide a harmless scratch identity rather than crashing the workbench
    # or writing beside the downloaded notebook on every slider move.
    _scratch_script = Path(tempfile.gettempdir()) / "pixcell_workbench_device.py"

    def rebuild(values):
        """Run the device's own script with knob overrides — the UI never
        reimplements geometry. @gf.cell caches globally by cell name, so
        clear it or every rebuild returns the first geometry."""
        try:
            gf.clear_cache()
        except Exception:
            pass
        ns = {
            "gf": gf,
            "gdsfactory": gf,
            "__name__": "__workbench__",
            "__file__": str(_scratch_script),
        }
        exec(SOURCE, ns)
        for k, v in values.items():
            ns[k] = v
        component = ns[MAIN_FUNCTION]()
        polys = []
        raw = component.get_polygons()
        if isinstance(raw, dict):
            for _layer, plist in raw.items():
                for poly in plist:
                    pts = [(pt.x / 1000.0, pt.y / 1000.0) for pt in poly.each_point_hull()]
                    if len(pts) >= 3:
                        polys.append(pts)
        # translate into the gate's scoring frame (the convention lives in
        # michaelangelo.core.compare_absolute.render_gds_absolute: left edge
        # to the target bbox, vertically centered on the footprint) — inlined
        # because this notebook must stay dependency-free of the repo. Without
        # it the drawn overlay AND the inlined IoU below diverge from the gate
        # on any script whose bbox is not anchored at the origin.
        if polys:
            _gx0 = min(x for poly in polys for x, _ in poly)
            _ys = [y for poly in polys for _, y in poly]
            _dy = ((FOOTPRINT_UM[1] / 2 - (min(_ys) + max(_ys)) / 2)
                   if FOOTPRINT_UM else -min(_ys))
            polys = [[(x - _gx0, y + _dy) for x, y in poly] for poly in polys]
        return component, polys

    knob_values = {**primary_knobs.value, **secondary_knobs.value}
    component, polygons = rebuild(knob_values)
    _xs = [x for poly in polygons for x, _ in poly]
    _ys = [y for poly in polygons for _, y in poly]
    bbox_um = (
        (max(_xs) - min(_xs), max(_ys) - min(_ys)) if _xs else (0.0, 0.0)
    )
    return bbox_um, component, gf, knob_values, polygons, rebuild


@app.cell
def _(CALIB, Image, TARGET_DATA_URI, base64, io, np):
    target_mask = None
    if TARGET_DATA_URI and CALIB:
        _payload = TARGET_DATA_URI.split(",", 1)[-1]
        _img = Image.open(io.BytesIO(base64.b64decode(_payload))).convert("L")
        target_mask = np.array(_img) < CALIB.get("white_threshold", 245)
    return (target_mask,)


@app.cell
def _(CALIB, FOOTPRINT_UM, ImageDraw, Image, bbox_um, np, polygons, target_mask):
    def _rasterize(polys):
        """The gate's math, inlined: rasterize at the calibrated absolute
        scale and score IoU on binary masks."""
        w, h = CALIB["image_size_px"]
        sx, sy = CALIB["scale_px_per_um"]
        offx, offy = CALIB.get("offset", (0, 0))
        img = Image.new("L", (int(w), int(h)), 255)
        drw = ImageDraw.Draw(img)
        for poly in polys:
            pts = [(offx + x * sx, offy + (FOOTPRINT_UM[1] - y) * sy) for x, y in poly]
            drw.polygon(pts, fill=0)
        return np.array(img) < CALIB.get("white_threshold", 245)

    iou = None
    if target_mask is not None and polygons:
        _r = _rasterize(polygons)
        _inter = np.logical_and(_r, target_mask).sum()
        _union = np.logical_or(_r, target_mask).sum()
        iou = float(_inter) / float(_union) if _union else 1.0

    fits = None
    if FOOTPRINT_UM:
        fits = (bbox_um[0] <= FOOTPRINT_UM[0] * 1.005
                and bbox_um[1] <= FOOTPRINT_UM[1] * 1.005)
    return fits, iou


@app.cell
def _(CALIB, FOOTPRINT_UM, LightTable, PROVENANCE, TARGET_DATA_URI, fits, iou, mo,
      polygons):
    _ghost = TARGET_DATA_URI or ""
    _calib = None
    if CALIB:
        _calib = {
            "sx": CALIB["scale_px_per_um"][0], "sy": CALIB["scale_px_per_um"][1],
            "offx": CALIB.get("offset", (0, 0))[0], "offy": CALIB.get("offset", (0, 0))[1],
            "w": CALIB["image_size_px"][0], "h": CALIB["image_size_px"][1],
        }
    table = mo.ui.anywidget(LightTable(
        polygons=[[list(pt) for pt in poly] for poly in polygons],
        footprint_um=list(FOOTPRINT_UM) if FOOTPRINT_UM else None,
        violation=(fits is False),
        ghost_data_uri=_ghost,
        calib=_calib,
        iou=iou,
        gate_iou=PROVENANCE.get("iou"),
        fits=fits,
    ))
    return (table,)


@app.cell
def _(DEVICE_NAME, PROVENANCE, mo):
    _ident = PROVENANCE.get("device_identification") or ""
    _gate_iou = PROVENANCE.get("iou")
    _badge = (
        f'<span class="wb-badge">GATE ✓ IoU {_gate_iou:.4f} recomputed</span>'
        if _gate_iou is not None else ""
    )
    masthead = mo.Html(
        f'<div class="wb wb-masthead">'
        f'<span class="wb-name">{DEVICE_NAME}</span>'
        f'<span class="wb-class">{_ident}</span>{_badge}</div>'
    )
    masthead
    return


@app.cell
def _(bbox_um, fits, iou, mo):
    _iou_html = (
        f'<div class="wb-iou{"" if (iou or 0) >= 0.85 else " fail"}">{iou:.4f}</div>'
        f'<div class="wb-meter"><div class="wb-meter-track">'
        f'<div class="wb-meter-fill" style="width:{max(0.0, min(1.0, iou)) * 100:.1f}%"></div>'
        f'</div></div>'
        if iou is not None
        else '<div class="wb-fit">no target image — fidelity unavailable</div>'
    )
    _fit_html = ""
    if fits is not None:
        _cls = "" if fits else " fail"
        _mark = "within budget" if fits else "EXCEEDS FOOTPRINT"
        _fit_html = (
            f'<div class="wb-fit{_cls}">'
            f'{bbox_um[0]:.2f} × {bbox_um[1]:.2f} µm · {_mark}</div>'
        )
    fidelity_panel = mo.Html(
        f'<div class="wb wb-panel"><div class="wb-label">Fidelity</div>'
        f'{_iou_html}{_fit_html}</div>'
    )
    return (fidelity_panel,)


@app.cell
def _(PROVENANCE, mo):
    _rows = []
    _promoted = PROVENANCE.get("promoted")
    if _promoted is not None:
        _rows.append(
            f"<dt>Promotion</dt><dd>{'promoted' if _promoted else 'not promoted'}</dd>"
        )
    _verified = PROVENANCE.get("verified")
    if _verified is not None:
        _rows.append(
            f"<dt>Gate</dt><dd>{'verified' if _verified else 'not verified'}</dd>"
        )
    for _label, _key in [
        ("Blind classification", "device_identification"),
        ("Gate IoU (recomputed)", "iou"),
        ("Dice", "dice"),
        ("Claim", "claim"),
        ("Parameter check", "knob_status"),
        ("Record", "source"),
    ]:
        _v = PROVENANCE.get(_key)
        if _v is not None:
            if isinstance(_v, float):
                _v = f"{_v:.4f}"
            _rows.append(f"<dt>{_label}</dt><dd>{_v}</dd>")
    _knobs = PROVENANCE.get("function_defining_knobs") or []
    if _knobs:
        _rows.append("<dt>Function parameters</dt><dd>"
                     + ", ".join(f"<code>{k}</code>" for k in _knobs) + "</dd>")
    provenance_panel = mo.Html(
        '<div class="wb wb-panel">'
        '<div class="wb-label">Artifact record</div>'
        f'<dl class="wb-prov" style="margin:4px 0 0 0">{"".join(_rows)}</dl></div>'
    )
    return (provenance_panel,)


@app.cell
def _(component, knob_values, mo, tempfile):
    from pathlib import Path as _P

    _tmp = _P(tempfile.mkdtemp(prefix="wb_gds_")) / "device.gds"
    component.write_gds(str(_tmp))
    _bytes = _tmp.read_bytes()
    export_gds = mo.download(
        data=_bytes, filename="device.gds", label="Export current GDS"
    )
    _lines = [f"{k} = {v}" for k, v in knob_values.items()]
    export_note = mo.accordion({
        "Parameter values": mo.Html(
            '<div class="wb-cmd">' + "\\n".join(_lines) + "</div>")
    })
    return export_gds, export_note


@app.cell
def _(HANDOFF_SCRIPT, mo):
    _retarget = (
        f"homi retarget {HANDOFF_SCRIPT} \\\\\\n"
        f"  --stack data/agents/pdk_swap/stacks/&lt;stack&gt;.json \\\\\\n"
        f"  --spec &lt;spec&gt;.json"
    )
    _simulate = f"homi simulate &lt;device.gds&gt;   # upload creates a DRAFT; you press Start"
    handoff_panel = mo.Html(
        '<div class="wb wb-panel">'
        '<div class="wb-label">Handoffs</div>'
        '<div style="display:flex; gap:18px; flex-wrap:wrap; margin-top:6px">'
        '<div style="flex:1; min-width:280px">'
        '<div class="wb-label" style="opacity:0.55">Retarget</div>'
        f'<div class="wb-cmd">{_retarget}</div></div>'
        '<div style="flex:1; min-width:280px">'
        '<div class="wb-label" style="opacity:0.55">Simulation draft</div>'
        f'<div class="wb-cmd">{_simulate}</div></div>'
        "</div></div>"
    )
    return (handoff_panel,)
__DRAW_CELLS__

@app.cell
def _(export_gds, export_note, fidelity_panel, handoff_panel, knob_panel, mo,
      provenance_panel, table):
    _right = mo.vstack(
        [knob_panel, fidelity_panel, export_gds, export_note], gap=0.8)
    explore_view = mo.vstack([
        mo.hstack([table, _right], widths=[2.2, 1], gap=1.0, align="start"),
        provenance_panel,
        handoff_panel,
    ], gap=0.8)
    __FINAL_VIEW__
    return


if __name__ == "__main__":
    app.run()
'''

# Draw-mode cells, appended only for the local variant. The ink table shares
# the light-table design; dispatch goes through the repo's own control plane
# (`homi generate` = dispatch worker + conductor gate + promote).
_DRAW_CELLS = '''

@app.cell
def _(InkTable, mo):
    ink = mo.ui.anywidget(InkTable())
    draw_len = mo.ui.number(value=20.0, step=0.1, label="footprint length (µm)")
    draw_wid = mo.ui.number(value=5.0, step=0.1, label="footprint width (µm)")
    draw_name = mo.ui.text(value="sketch1", label="project name")
    dispatch_btn = mo.ui.run_button(label="Dispatch recreation worker")
    return dispatch_btn, draw_len, draw_name, draw_wid, ink


@app.cell
def _(Path, base64, dispatch_btn, draw_len, draw_name, draw_wid, ink, json, mo):
    import subprocess
    import sys

    REPO = Path(__REPO_ROOT__)
    dispatch_status = None
    if dispatch_btn.value:
        _uri = ink.ink_data_uri
        if not _uri:
            dispatch_status = "Draw the device first — black strokes on the table."
        else:
            _proj = REPO / "projects" / draw_name.value
            _proj.mkdir(parents=True, exist_ok=True)
            (_proj / "device_bw.png").write_bytes(
                base64.b64decode(_uri.split(",", 1)[1]))
            (_proj / "footprint.json").write_text(
                json.dumps({"footprint_um": [draw_len.value, draw_wid.value]}))
            _log = _proj / "recreation.log"
            with open(_log, "w") as _fh:
                subprocess.Popen(
                    [str(REPO / ".venv" / "bin" / "python"), "-m", "homi.cli",
                     "generate", str(_proj)],
                    cwd=str(REPO), stdout=_fh, stderr=subprocess.STDOUT,
                )
            dispatch_status = (
                f"Worker dispatched for projects/{draw_name.value} — the gate "
                f"will verify before anything is promoted. Watch below."
            )
    return REPO, dispatch_status


@app.cell
def _(REPO, dispatch_status, draw_name, mo):
    watch = mo.ui.refresh(default_interval="2s") if dispatch_status else None
    watch
    return (watch,)


@app.cell
def _(Path, REPO, dispatch_status, draw_name, mo, watch):
    draw_progress = mo.Html("")
    if dispatch_status:
        _ = watch.value if watch is not None else None
        _proj = REPO / "projects" / draw_name.value
        _best = _proj / "output" / "best.gds"
        _log = _proj / "recreation.log"
        _tail = ""
        if _log.exists():
            _tail = "".join(_log.read_text().splitlines(keepends=True)[-8:])
        _state = ("<b>gate-verified — regenerate the workbench for the new "
                  "device:</b><br><code>homi explore "
                  f"projects/{draw_name.value}/output/best.py</code>"
                  if _best.exists() else "worker running…")
        draw_progress = mo.Html(
            f'<div class="wb wb-panel">{dispatch_status}<br><br>{_state}'
            f'<div class="wb-cmd" style="margin-top:8px">{_tail}</div></div>'
        )
    draw_progress
    return


@app.cell
def _(dispatch_btn, draw_len, draw_name, draw_wid, ink, mo):
    draw_view = mo.vstack([
        mo.Html('<div class="wb-label">Draw · black = material · footprint sets the scale</div>'),
        ink,
        mo.hstack([draw_len, draw_wid, draw_name, dispatch_btn],
                  gap=0.8, align="end", wrap=True),
    ], gap=0.6)
    return (draw_view,)


@app.cell
def _(mo):
    # NOT mo.ui.tabs: UI containers CLONE their children, which resets the
    # light table's traits to defaults. A radio switch keeps layout plain.
    mode = mo.ui.radio(options=["Explore", "Draw"], value="Explore", inline=True)
    return (mode,)
'''


# A designed knob row set (marimo's sliders live in closed shadow DOM and
# can't be restyled): silkscreen labels, hairline track, chrome thumb, mono
# values. Values commit on release — no rebuild storms mid-drag.
_KNOB_PANEL_ESM = r"""
const CSS = `
.kp { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  column-gap: 22px; row-gap: 2px; }
.kp-row { margin: 0 0 4px 0; }
.kp-head { display: flex; justify-content: space-between; align-items: baseline; }
.kp-name { font-size: 11.5px; letter-spacing: 0.01em; text-transform: capitalize;
  color: #3E4348; opacity: 0.85; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; }
.kp-val { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px; color: #17191C; font-variant-numeric: tabular-nums;
  cursor: text; border-bottom: 1px dashed transparent; }
.kp-val:hover { border-bottom-color: #DBD9D2; }
.kp-val input { font: inherit; color: inherit; width: 72px; border: none;
  border-bottom: 1px solid #17191C; outline: none; text-align: right;
  background: transparent; padding: 0; }
.kp-track { position: relative; height: 16px; cursor: ew-resize; }
.kp-track::before { content: ""; position: absolute; left: 0; right: 0;
  top: 7px; height: 2px; background: #DBD9D2; }
.kp-fill { position: absolute; left: 0; top: 7px; height: 2px; background: #3E4348; }
.kp-thumb { position: absolute; top: 2px; width: 6px; height: 12px;
  background: #17191C; border-radius: 1px; transform: translateX(-3px); }
`;
function render({ model, el }) {
  el.innerHTML = "";
  const style = document.createElement("style");
  style.textContent = CSS;
  el.appendChild(style);
  const root = document.createElement("div");
  root.className = "kp";
  el.appendChild(root);

  const knobs = model.get("knobs") || [];
  const values = Object.assign({}, model.get("values") || {});

  for (const k of knobs) {
    const row = document.createElement("div");
    row.className = "kp-row";
    const head = document.createElement("div");
    head.className = "kp-head";
    const name = document.createElement("span");
    name.className = "kp-name";
    name.textContent = k.label || k.name;
    const val = document.createElement("span");
    val.className = "kp-val";
    head.appendChild(name); head.appendChild(val);
    const track = document.createElement("div");
    track.className = "kp-track";
    const fill = document.createElement("div");
    fill.className = "kp-fill";
    const thumb = document.createElement("div");
    thumb.className = "kp-thumb";
    track.appendChild(fill); track.appendChild(thumb);
    row.appendChild(head); row.appendChild(track);
    root.appendChild(row);

    const lo = k.min_value, hi = k.max_value;
    const decimals = (k.step && k.step < 0.01) ? 4 : (k.step < 0.1 ? 3 : 2);
    function show(v) {
      const t = Math.max(0, Math.min(1, (v - lo) / (hi - lo || 1)));
      const w = track.clientWidth || 200;
      fill.style.width = (t * w) + "px";
      thumb.style.left = (t * w) + "px";
      val.textContent = Number(v).toFixed(decimals);
    }
    let v = values[k.name] ?? k.default_value;
    requestAnimationFrame(() => show(v));

    let dragging = false;
    function fromEvent(e) {
      const r = track.getBoundingClientRect();
      const t = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
      let nv = lo + t * (hi - lo);
      if (k.step) nv = Math.round(nv / k.step) * k.step;
      return Math.max(lo, Math.min(hi, nv));
    }
    track.addEventListener("pointerdown", (e) => {
      dragging = true;
      track.setPointerCapture(e.pointerId);
      v = fromEvent(e); show(v);
    });
    track.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      v = fromEvent(e); show(v);
    });
    track.addEventListener("pointerup", () => {
      dragging = false;
      values[k.name] = v;
      model.set("values", Object.assign({}, values));  // commit on release
      model.save_changes();
    });
    // click the value to type it exactly
    val.addEventListener("click", () => {
      if (val.querySelector("input")) return;
      const inp = document.createElement("input");
      inp.value = Number(v).toFixed(decimals);
      val.textContent = "";
      val.appendChild(inp);
      inp.focus(); inp.select();
      const commit = () => {
        const nv = parseFloat(inp.value);
        if (!Number.isNaN(nv)) {
          v = Math.max(lo, Math.min(hi, nv));
          values[k.name] = v;
          model.set("values", Object.assign({}, values));
          model.save_changes();
        }
        val.textContent = Number(v).toFixed(decimals);
        show(v);
      };
      inp.addEventListener("keydown", (e) => {
        if (e.key === "Enter") inp.blur();
        if (e.key === "Escape") { inp.value = String(v); inp.blur(); }
      });
      inp.addEventListener("blur", commit, { once: true });
    });
    new ResizeObserver(() => show(v)).observe(track);
  }
}
export default { render };
"""

# Resolved widget sources — shared by the generated workbench notebooks and
# by homi.studio_app (which imports them directly).
LIGHT_TABLE_ESM = _LIGHT_TABLE_ESM.replace("__WIDGET_STYLE__", _WIDGET_STYLE).replace(
    "__PHOTONIC_KINDS_JS__", _PHOTONIC_KINDS_JS
)
INK_TABLE_ESM = _INK_TABLE_ESM.replace("__WIDGET_STYLE__", _WIDGET_STYLE).replace(
    "__PHOTONIC_KINDS_JS__", _PHOTONIC_KINDS_JS
)
KNOB_PANEL_ESM = _KNOB_PANEL_ESM
DESIGN_CSS = _CSS


def _py(value) -> str:
    """Embed a value as a Python literal in the generated notebook."""
    return repr(value)


def write_workbench(
    script_path: Path | str,
    out_path: Path | str,
    *,
    device_name: str,
    params: list[dict],
    function_knobs: list[str] | None = None,
    provenance: dict | None = None,
    footprint_um: tuple[float, float] | None = None,
    calibration: dict | None = None,
    target_png: Path | str | None = None,
    draw: bool = False,
    repo_root: Path | str | None = None,
    handoff_script: str | None = None,
) -> Path:
    """Emit the workbench notebook. Everything embedded at generation time."""
    script_path = Path(script_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    source = script_path.read_text()
    # main function: the last `def <name>()` decorated with @gf.cell, else guess
    import re as _re

    m = _re.findall(r"@gf\.cell\s*\ndef\s+(\w+)\s*\(", source)
    main_function = m[-1] if m else "device"

    target_data_uri = None
    if target_png and Path(target_png).exists():
        target_bytes = Path(target_png).read_bytes()
        import base64 as _base64

        target_data_uri = "data:image/png;base64," + _base64.b64encode(
            target_bytes).decode("ascii")
        # Keep the companion image for backwards-compatible CLI workbench
        # directories, even though the notebook no longer depends on it.
        shutil.copy2(target_png, out_path.parent / "target.png")

    text = _TEMPLATE
    draw_cells = ""
    if draw:
        draw_cells = _DRAW_CELLS.replace(
            "__REPO_ROOT__", _py(str(repo_root or Path.cwd()))
        )
        final_view = (
            "_active = explore_view if mode.value == \"Explore\" else draw_view\n"
            "    view = mo.vstack([mode, _active], gap=0.6)\n"
            "    view"
        )
    else:
        final_view = "explore_view"

    # the layout cell needs draw_view + mode in its signature only when they exist
    if draw:
        text = text.replace(
            "def _(export_gds, export_note, fidelity_panel, handoff_panel, knob_panel, mo,\n"
            "      provenance_panel, table):",
            "def _(draw_view, export_gds, export_note, fidelity_panel, handoff_panel,\n"
            "      knob_panel, mo, mode, provenance_panel, table):",
        )

    subs = {
        "__DEVICE_NAME__": _py(device_name),
        "__SOURCE__": _py(source),
        "__MAIN_FUNCTION__": _py(main_function),
        "__PARAMS__": _py(params),
        "__FUNCTION_KNOBS__": _py(function_knobs or []),
        "__PROVENANCE__": _py(provenance or {}),
        "__FOOTPRINT_UM__": _py(list(footprint_um) if footprint_um else None),
        "__CALIB__": _py(calibration),
        "__TARGET_DATA_URI__": _py(target_data_uri),
        "__DRAW_MODE__": _py(bool(draw)),
        "__HANDOFF_SCRIPT__": _py(handoff_script or str(script_path)),
        "__CSS__": _py(_CSS),
        "__LIGHT_TABLE_ESM__": _py(LIGHT_TABLE_ESM),
        "__INK_TABLE_ESM__": _py(INK_TABLE_ESM),
        "__DRAW_CELLS__": draw_cells,
        "__FINAL_VIEW__": final_view,
    }
    for key, value in subs.items():
        text = text.replace(key, value if key in ("__DRAW_CELLS__", "__FINAL_VIEW__", "__HANDOFF_SCRIPT__") else value)

    out_path.write_text(text)
    return out_path


def generate_workbench(script_path: Path | str, output_dir: Path | str | None = None,
                       *, draw: bool = False,
                       handoff_script: str | None = None) -> Path:
    """Collect everything from the project layout and emit the workbench.

    projects/<name>/output/best.py is the canonical input; recreation
    workdirs beside it supply target/calibration/provenance.
    """
    import json as _json

    from homi.paths import repo_root
    from homi.weber_integration import get_live_parameter_info

    script_path = Path(script_path).resolve()
    output_dir = Path(output_dir).resolve() if output_dir else script_path.parent
    if script_path.parent.name == "output":
        project_dir = script_path.parent.parent
        device_name = script_path.parent.parent.name
    else:
        project_dir = script_path.parent
        device_name = script_path.stem

    source = script_path.read_text()
    params = get_live_parameter_info(source)

    provenance: dict = {}
    function_knobs: list[str] = []
    target_png = calibration = footprint_um = None
    for recreation_dir in sorted(script_path.parent.glob("recreation_*")):
        mfile = recreation_dir / "metrics_abs.json"
        lfile = recreation_dir / "recreation_log.json"
        cfile = recreation_dir / "calibration.json"
        tfile = recreation_dir / "component.png"
        if mfile.exists():
            m = _json.loads(mfile.read_text())
            provenance["iou"] = m.get("IoU") or m.get("iou")
            provenance["dice"] = m.get("Dice") or m.get("dice")
            provenance["source"] = str(mfile.relative_to(project_dir))
        if lfile.exists():
            log = _json.loads(lfile.read_text())
            topo = log.get("topology_reasoning") or {}
            provenance["device_identification"] = topo.get("device_identification")
            function_knobs = topo.get("function_defining_knobs") or []
        if cfile.exists():
            calibration = _json.loads(cfile.read_text())
        if tfile.exists():
            target_png = tfile

    # The conductor record is the authority for a promoted artifact. Older
    # projects may only have recreation metrics, so retain those values above
    # and override them field-by-field when output/gate.json is available.
    gate_file = project_dir / "output" / "gate.json"
    if gate_file.exists():
        try:
            gate = _json.loads(gate_file.read_text())
        except (OSError, ValueError):
            gate = None
        if isinstance(gate, dict):
            for key in (
                "verified", "promoted", "claim", "claimed_iou", "purity",
                "knob", "knob_status", "strict", "reasons", "gated_at",
            ):
                if key in gate:
                    provenance[key] = gate[key]
            if "iou" in gate:
                provenance["iou"] = gate["iou"]
            gate_metrics = gate.get("metrics")
            if isinstance(gate_metrics, dict):
                if "Dice" in gate_metrics:
                    provenance["dice"] = gate_metrics["Dice"]
                elif "dice" in gate_metrics:
                    provenance["dice"] = gate_metrics["dice"]
            provenance["source"] = "output/gate.json"

    fp_file = project_dir / "footprint.json"
    if fp_file.exists():
        fp = _json.loads(fp_file.read_text()).get("footprint_um")
        if fp:
            footprint_um = (float(fp[0]), float(fp[1]))
    if footprint_um is None and calibration and calibration.get("footprint_um"):
        fp = calibration["footprint_um"]
        footprint_um = (float(fp[0]), float(fp[1]))

    return write_workbench(
        script_path,
        output_dir / "workbench.py",
        device_name=device_name,
        params=params,
        function_knobs=function_knobs,
        provenance=provenance,
        footprint_um=footprint_um,
        calibration=calibration,
        target_png=target_png,
        draw=draw,
        repo_root=repo_root(),
        handoff_script=handoff_script,
    )
