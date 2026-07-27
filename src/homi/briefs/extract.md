Extract the photonic DEVICE schematic into a clean image + footprint.

Input: {{INPUT}}
Output dir: {{OUTPUT_DIR}}
{{HINT_LINE}}{{INPUT_NOTE}}
Do it AGENT-FIRST — use your own eyes, no VLM API scoring:
1. If the input is a PDF: call analyze_pdf_figures("{{INPUT}}") to see which pages hold
   figures. Vector-drawn figures have high vector_draw_ops and 0 embedded_images —
   extract_images_from_pdf cannot see them. Use recommend_render.
2. render_pdf_pages on the recommend_render pages.
3. READ each rendered page yourself; pick the page with the device schematic (top-down
   waveguide layout, ports at edges, dimension labels) and read off a tight pixel bbox.
4. crop_region(page_image_path, bbox, output_path); then READ the crop back to verify it
   is tight and complete; adjust the bbox and re-crop if needed.
5. Produce the clean black-and-white device image (generate_bw_variants, READ the
   variants, pick the best, refine_bw_image if needed) and save it as device_bw.png
   in the output dir.
6. Read the device dimensions (L, W, gaps, taper widths) from the figure/caption/tables
   and write footprint.json in the output dir via create_footprint_json.
7. CONDUCTOR-SIDE function notes: record what the paper SAYS the device is and any
   reported performance (FSR, transmission, splitting ratio, insertion loss,
   bandwidth, coupling efficiency) into {{OUTPUT_DIR}}/function.json:
   {"device_class_text": "<the paper's own words>",
    "claims": {"fsr_nm": 8.0, "transmission_min": 0.95, ...},
    "provenance": {"fsr_nm": "p.4, Fig 5", ...}}
   Only include numbers the paper actually states, each with its page/figure.
   This file is for the CONDUCTOR (spec authoring) — recreation workers never
   read it; their only ground truth is the image + footprint.

Tooling: if you have MCP tools, these are the mcp__homi-mj__* family. Without MCP
tools (e.g. a Codex worker), the same functions are importable from the installed
package: {{PYTHON}} -c "from homi.paper_processing import analyze_pdf_figures,
crop_region, generate_bw_variants, refine_bw_image, get_gemini_client" — the B&W
generators take client=get_gemini_client(), which reads GEMINI_API_KEY from the
environment or a .env file. For page rendering use PyMuPDF (fitz) directly at ~2x zoom. If no
create_footprint_json tool is available, write the JSON yourself:
{"footprint_um": [L, W]}. View rendered images with your own vision.

The deliverables are exactly: {{OUTPUT_DIR}}/device_bw.png and {{OUTPUT_DIR}}/footprint.json.
End your turn with "EXTRACT DONE: files=<n>" when they exist, or "EXTRACT BLOCKED: <why>".
