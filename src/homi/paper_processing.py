"""
Paper Processing Module

Extracts device images from research papers and converts them to B&W representations.
Refactored from mj/paper_processor.py for use with Streamlit.
"""

import hashlib
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Callable, Optional

try:
    import fitz  # PyMuPDF
    from PIL import Image
    from google import genai
    from google.genai import types
except ImportError as e:
    raise ImportError(f"Missing dependency: {e}. Run: ./setup.sh (or `uv sync`)")


def get_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    """Get Gemini client with API key from env or parameter."""
    # Load .env (upward search / checkout / ~/.pixcell/env)
    from homi.paths import load_env
    load_env()

    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Set it in environment or .env file.")
    return genai.Client(api_key=api_key)


def get_image_mime_type(image_path: str) -> str:
    """Get MIME type for an image file."""
    ext = Path(image_path).suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return mime_types.get(ext, "image/png")


def extract_images_from_pdf(
    pdf_path: str,
    output_dir: str,
    min_size_bytes: int = 5000,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> list[dict]:
    """
    Extract all images from a PDF, deduplicating by content hash.

    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save extracted images
        min_size_bytes: Minimum image size to include (default 5KB)
        progress_callback: Optional callback(current, total) for progress updates

    Returns:
        List of dicts with 'path', 'index', 'page_num', 'size_bytes'
    """
    images = []
    seen_hashes = set()
    seen_xrefs = set()

    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    for page_num in range(total_pages):
        if progress_callback:
            progress_callback(page_num + 1, total_pages)

        page = doc[page_num]
        image_list = page.get_images()

        for img_index, img in enumerate(image_list):
            xref = img[0]

            # Skip duplicates
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # Skip small images
                if len(image_bytes) < min_size_bytes:
                    continue

                # Skip content duplicates
                img_hash = hashlib.md5(image_bytes).hexdigest()
                if img_hash in seen_hashes:
                    continue
                seen_hashes.add(img_hash)

                # Save image
                img_filename = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                img_path = os.path.join(output_dir, img_filename)

                with open(img_path, "wb") as f:
                    f.write(image_bytes)

                images.append({
                    "path": img_path,
                    "index": len(images),
                    "page_num": page_num + 1,
                    "size_bytes": len(image_bytes)
                })
            except Exception as e:
                print(f"Warning: Could not extract image {img_index} from page {page_num + 1}: {e}")

    doc.close()
    return images


VECTOR_FIGURE_THRESHOLD = 20  # ≥ this many vector draw ops on a page ⇒ likely a drawn figure


def analyze_pdf_figures(pdf_path: str) -> dict:
    """Per-page diagnostic of a PDF's figure content — NO API calls.

    For each page, reports how many embedded raster images it has and how many
    vector draw operations. Vector-drawn figures (TikZ/matplotlib-PDF) are
    invisible to extract_images_from_pdf's page.get_images(); this lets a driving
    agent see which pages to render.

    Returns:
        {"pages": [{"page_num", "embedded_images", "vector_draw_ops", "likely_figure"}],
         "total_pages": int, "recommend_render": [page_num, ...]}
    """
    doc = fitz.open(pdf_path)
    pages = []
    recommend = []
    for i in range(len(doc)):
        page = doc[i]
        n_emb = len(page.get_images())
        n_vec = len(page.get_drawings())
        likely = n_emb > 0 or n_vec >= VECTOR_FIGURE_THRESHOLD
        pages.append({
            "page_num": i + 1,
            "embedded_images": n_emb,
            "vector_draw_ops": n_vec,
            "likely_figure": likely,
        })
        if likely:
            recommend.append(i + 1)
    total = len(doc)
    doc.close()
    return {"pages": pages, "total_pages": total, "recommend_render": recommend}


def crop_region(
    page_image_path: str,
    bbox: dict,
    output_path: str,
    pad_frac: float = 0.0,
) -> dict:
    """Crop a rectangular region from an image — NO API calls.

    The DRIVING AGENT supplies the bbox (it read the page with its own eyes).
    This is the keyless half of the old extract_figure_from_page: perception is
    the agent's job; this tool just cuts the pixels.

    Args:
        page_image_path: image to crop (usually a rendered PDF page).
        bbox: {"x1","y1","x2","y2"} in pixels of page_image_path.
        output_path: where to save the crop.
        pad_frac: optional fraction to expand the box on each side (default 0).

    Returns dict with output_path, bbox_applied (clamped), cropped_size.
    Raises ValueError on a degenerate bbox.
    """
    x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"degenerate bbox (x2<=x1 or y2<=y1): {bbox}")

    img = Image.open(page_image_path)
    W, H = img.size
    if pad_frac:
        px = int((x2 - x1) * pad_frac)
        py = int((y2 - y1) * pad_frac)
        x1, y1, x2, y2 = x1 - px, y1 - py, x2 + px, y2 + py

    x1 = max(0, int(x1))
    y1 = max(0, int(y1))
    x2 = min(W, int(x2))
    y2 = min(H, int(y2))

    # A box wholly outside the image survives the pre-clamp degeneracy check but
    # reverses here (e.g. x1=150,x2=200 on a 100px image -> x1=150,x2=100).
    # Reject it with a clear error instead of letting PIL raise a generic one.
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"bbox does not overlap the {W}x{H} image after clamping: {bbox}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.crop((x1, y1, x2, y2)).save(output_path)
    return {
        "output_path": str(output_path),
        "bbox_applied": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        "cropped_size": {"width": x2 - x1, "height": y2 - y1},
    }


def score_images(
    images: list[dict],
    client: genai.Client = None,
    min_score: int = 5,
    batch_size: int = 10,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> list[dict]:
    """
    DEPRECATED (v1): perception moved to the driving agent (agent-first extraction);
    kept only for homi/api.py and app.py until they are rewired (fast-follow).
    No longer exposed as an MCP tool — see analyze_pdf_figures + crop_region.

    Score each image for containing a device schematic.

    Uses Gemini vision to score each image for how well it depicts a device schematic.

    Args:
        images: List of image dicts from extract_images_from_pdf
        client: Gemini client (created on demand if not provided)
        min_score: Minimum score to include (0-10)
        batch_size: Images per API call
        progress_callback: Optional callback(current, total) for progress

    Returns:
        Filtered list of images with score >= min_score, sorted by score descending
    """
    if client is None:
        client = get_gemini_client()

    scored_images = []
    total_batches = (len(images) + batch_size - 1) // batch_size

    for batch_idx, batch_start in enumerate(range(0, len(images), batch_size)):
        if progress_callback:
            progress_callback(batch_idx + 1, total_batches)

        batch = images[batch_start:batch_start + batch_size]

        # Build content for this batch
        content_parts = []
        content_parts.append(types.Part.from_text(text="""Score each image from 0-10 for how likely it contains a photonic DEVICE schematic/structure.

HIGH scores (7-10): Device schematics, waveguide layouts, SEM images of fabricated devices, simulation results showing device geometry
MEDIUM scores (4-6): Figures that might contain device info but also have graphs/text
LOW scores (0-3): Pure graphs/charts, experimental setups, block diagrams, text-heavy figures

For each image, respond with ONLY a JSON array of objects:
[{"index": <number>, "score": <0-10>, "reason": "<brief>"}]
"""))

        for img_info in batch:
            content_parts.append(types.Part.from_text(text=f"\n--- Image index {img_info['index']} ---"))
            try:
                with open(img_info["path"], "rb") as f:
                    image_bytes = f.read()
                mime_type = get_image_mime_type(img_info["path"])
                content_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
            except Exception as e:
                print(f"Warning: Could not load {img_info['path']}: {e}")
                continue

        content_parts.append(types.Part.from_text(text="\n\nProvide scores as JSON array:"))

        try:
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=content_parts,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_level="high"
                    )
                )
            )
            response_text = response.text.strip()

            # Parse JSON
            if "```" in response_text:
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            scores = json.loads(response_text)

            # Add scores to images
            score_map = {s["index"]: s for s in scores}
            for img in batch:
                if img["index"] in score_map:
                    img["score"] = score_map[img["index"]]["score"]
                    img["score_reason"] = score_map[img["index"]].get("reason", "")
                    if img["score"] >= min_score:
                        scored_images.append(img)

        except Exception as e:
            print(f"Warning: Scoring failed for batch: {e}")
            # Include all images from failed batch with default score
            for img in batch:
                img["score"] = 5
                img["score_reason"] = "Scoring failed"
                scored_images.append(img)

    # Sort by score descending
    scored_images.sort(key=lambda x: x.get("score", 0), reverse=True)
    return scored_images


def generate_bw_variants(
    image_path: str,
    client: genai.Client,
    output_dir: str,
    num_variants: int = 5,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> list[str]:
    """
    Generate B&W variants of an image using Gemini image generation.

    Args:
        image_path: Path to source image
        client: Gemini client
        output_dir: Directory to save variants
        num_variants: Number of variants to generate
        progress_callback: Optional callback(current, total) for progress

    Returns:
        List of paths to generated variant images
    """
    # Load the image
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    mime_type = get_image_mime_type(image_path)

    prompt = """Make this image completely black and white. Only the device in black and everything else in white. Get rid of the text and everything else please.

Generate a clean image showing ONLY the device structure/geometry as a black silhouette on a pure white background. Remove all:
- Text and labels
- Axes and scale bars
- Color gradients
- Background elements

The output should be a simple, clean black shape representing the device geometry."""

    os.makedirs(output_dir, exist_ok=True)
    generated_paths = []

    for i in range(num_variants):
        if progress_callback:
            progress_callback(i + 1, num_variants)

        try:
            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"]
                )
            )

            # Extract generated image from response
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_data = part.inline_data.data
                    variant_path = os.path.join(output_dir, f"variant_{i + 1}.png")
                    img = Image.open(io.BytesIO(image_data))
                    img.save(variant_path)
                    generated_paths.append(variant_path)
                    break

        except Exception as e:
            print(f"Warning: Failed to generate variant {i + 1}: {e}")

    return generated_paths


def refine_bw_image(
    source_image_path: str,
    client: genai.Client,
    output_dir: str,
    custom_instructions: str,
    num_variants: int = 2,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> list[str]:
    """
    Refine a B&W image based on custom user instructions.

    Args:
        source_image_path: Path to source image (original or existing B&W variant)
        client: Gemini client
        output_dir: Directory to save refined variants
        custom_instructions: User's refinement instructions
        num_variants: Number of refined variants to generate
        progress_callback: Optional callback(current, total) for progress

    Returns:
        List of paths to generated refined variant images
    """
    # Load the source image
    with open(source_image_path, "rb") as f:
        image_bytes = f.read()
    mime_type = get_image_mime_type(source_image_path)

    # Construct prompt with user instructions
    prompt = f"""You are refining a black and white device image.

The source image shows a photonic device structure. It may be an original colored/grayscale image OR an already-processed black and white silhouette.

USER'S REFINEMENT REQUEST:
{custom_instructions}

REFINEMENT RULES:
1. Keep the overall device structure intact unless explicitly told to change it
2. The output MUST be a black device silhouette on a pure white background
3. Apply the user's specific modifications precisely
4. Remove any artifacts, text, labels, or unwanted elements
5. Ensure clean, sharp edges on the device geometry

Generate a refined version that addresses the user's specific request while maintaining a clean black-on-white device silhouette."""

    os.makedirs(output_dir, exist_ok=True)
    generated_paths = []

    for i in range(num_variants):
        if progress_callback:
            progress_callback(i + 1, num_variants)

        try:
            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"]
                )
            )

            # Extract generated image from response
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_data = part.inline_data.data
                    variant_path = os.path.join(output_dir, f"refined_{i + 1}.png")
                    img = Image.open(io.BytesIO(image_data))
                    img.save(variant_path)
                    generated_paths.append(variant_path)
                    break

        except Exception as e:
            print(f"Warning: Failed to generate refined variant {i + 1}: {e}")

    return generated_paths


def load_image_as_bytes(image_path: str) -> tuple[bytes, str]:
    """Load image and return (bytes, mime_type)."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    mime_type = get_image_mime_type(image_path)
    return image_bytes, mime_type


def save_selected_image(source_path: str, dest_path: str) -> str:
    """Copy selected image to destination, converting to PNG if needed."""
    img = Image.open(source_path)
    img.save(dest_path)
    return dest_path
