"""
MJ MCP Server - Paper Processing & Device Image Extraction

Tools for extracting device representations from silicon photonics
research papers. Uses Gemini for image analysis and B&W conversion.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.types import TextContent, Tool

from .base import BaseMCPServer, TaskStatus, serialize_result, tool_handler

# Load environment variables (.env upward from cwd / checkout / ~/.pixcell/env)
from homi.paths import load_env
load_env()

# Lazy imports for dependencies
_PIL_Image = None
_fitz = None
_genai = None
_skimage_metrics = None


def _get_pil():
    global _PIL_Image
    if _PIL_Image is None:
        from PIL import Image
        _PIL_Image = Image
    return _PIL_Image


def _get_fitz():
    global _fitz
    if _fitz is None:
        import fitz
        _fitz = fitz
    return _fitz


def _get_genai():
    global _genai
    if _genai is None:
        from google import genai
        _genai = genai
    return _genai


def _get_skimage_metrics():
    global _skimage_metrics
    if _skimage_metrics is None:
        from skimage import metrics
        _skimage_metrics = metrics
    return _skimage_metrics




logger = logging.getLogger(__name__)

# Thread pool for blocking operations
_executor = ThreadPoolExecutor(max_workers=4)


class MJServer(BaseMCPServer):
    """
    MCP Server for MJ (Paper Processing).

    Provides tools for:
    - Extracting images from PDF papers
    - Scoring images for device content using Gemini
    - Generating B&W variants of device images
    - Computing image similarity metrics
    """

    server_name = "homi-mj"
    server_version = "0.1.0"

    def __init__(self):
        super().__init__()
        self._gemini_client = None

    def _get_gemini_client(self):
        """Get or create Gemini client."""
        if self._gemini_client is None:
            genai = _get_genai()
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            self._gemini_client = genai.Client(api_key=api_key)
        return self._gemini_client

    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="extract_images_from_pdf",
                description=(
                    "Extract all images from a PDF file. Returns list of image paths "
                    "with metadata (page number, size, type). Deduplicates by content hash."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pdf_path": {
                            "type": "string",
                            "description": "Path to the PDF file"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Directory to save extracted images"
                        },
                        "min_size_bytes": {
                            "type": "integer",
                            "description": "Minimum image size in bytes (default: 5000)",
                            "default": 5000
                        }
                    },
                    "required": ["pdf_path", "output_dir"]
                }
            ),
            Tool(
                name="generate_bw_variants",
                description=(
                    "Generate B&W variants of a device image using Gemini image generation. "
                    "Creates multiple clean silhouette versions for selection."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the source device image"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Directory to save B&W variants"
                        },
                        "num_variants": {
                            "type": "integer",
                            "description": "Number of variants to generate (default: 5)",
                            "default": 5
                        }
                    },
                    "required": ["image_path", "output_dir"]
                }
            ),
            Tool(
                name="refine_bw_image",
                description=(
                    "Refine a B&W device image based on custom instructions. "
                    "Use this when the initial B&W conversion needs adjustments like "
                    "removing artifacts, sharpening edges, or fixing specific regions."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source_image_path": {
                            "type": "string",
                            "description": "Path to the source image (original or B&W variant to refine)"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Directory to save refined variants"
                        },
                        "custom_instructions": {
                            "type": "string",
                            "description": "Specific refinement instructions (e.g., 'remove the circle on the left', 'sharpen the waveguide edges')"
                        },
                        "num_variants": {
                            "type": "integer",
                            "description": "Number of refined variants to generate (default: 2)",
                            "default": 2
                        }
                    },
                    "required": ["source_image_path", "output_dir", "custom_instructions"]
                }
            ),
            Tool(
                name="compute_image_similarity",
                description=(
                    "Compute similarity metrics between two images. Returns SSIM "
                    "(structural similarity), MSE, and other metrics for comparison."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image1_path": {
                            "type": "string",
                            "description": "Path to first image"
                        },
                        "image2_path": {
                            "type": "string",
                            "description": "Path to second image"
                        }
                    },
                    "required": ["image1_path", "image2_path"]
                }
            ),
            Tool(
                name="get_image_metadata",
                description=(
                    "Get metadata about an image file including dimensions, "
                    "format, color mode, and file size."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the image file"
                        }
                    },
                    "required": ["image_path"]
                }
            ),
            # PDF page rendering (captures vector graphics)
            Tool(
                name="render_pdf_pages",
                description=(
                    "Render PDF pages as images. Unlike extract_images_from_pdf which only gets "
                    "embedded raster images, this renders full pages including vector graphics. "
                    "Use this when device schematics are drawn as vector graphics in the PDF."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pdf_path": {
                            "type": "string",
                            "description": "Path to the PDF file"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Directory to save rendered page images"
                        },
                        "pages": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Page numbers to render (1-indexed). If not specified, renders first 5 pages."
                        },
                        "scale": {
                            "type": "number",
                            "description": "Scale factor for rendering (default: 2.0 for higher quality)",
                            "default": 2.0
                        }
                    },
                    "required": ["pdf_path", "output_dir"]
                }
            ),
            Tool(
                name="analyze_pdf_figures",
                description=(
                    "Per-page diagnostic of a PDF (NO API calls): embedded-image count + "
                    "vector-draw-op count per page, so you can see which pages hold "
                    "vector-drawn figures that extract_images_from_pdf cannot see. "
                    "Returns recommend_render page numbers to render next."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pdf_path": {"type": "string", "description": "Path to the PDF file"},
                    },
                    "required": ["pdf_path"],
                },
            ),
            Tool(
                name="crop_region",
                description=(
                    "Crop a rectangular region from an image (NO API calls). YOU supply the "
                    "bbox after reading the rendered page with your own eyes — this tool just "
                    "cuts the pixels. Use after render_pdf_pages to extract a device figure."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_image_path": {"type": "string", "description": "Image to crop (a rendered page)"},
                        "bbox": {
                            "type": "object",
                            "description": "Pixel box {x1,y1,x2,y2} in page_image_path",
                            "properties": {
                                "x1": {"type": "number"}, "y1": {"type": "number"},
                                "x2": {"type": "number"}, "y2": {"type": "number"},
                            },
                            "required": ["x1", "y1", "x2", "y2"],
                        },
                        "output_path": {"type": "string", "description": "Where to save the crop"},
                        "pad_frac": {"type": "number", "description": "Fraction to expand box each side (default 0)", "default": 0.0},
                    },
                    "required": ["page_image_path", "bbox", "output_path"],
                },
            ),
            Tool(
                name="create_footprint_json",
                description=(
                    "Create a footprint.json file with device dimensions. "
                    "Used by Michaelangelo for calibration."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "length_um": {
                            "type": "number",
                            "description": "Device length in micrometers"
                        },
                        "width_um": {
                            "type": "number",
                            "description": "Device width in micrometers"
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Path to save footprint.json"
                        }
                    },
                    "required": ["length_um", "width_um", "output_path"]
                }
            )
        ]

    async def handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Dispatch tool calls to handlers."""
        handlers = {
            "extract_images_from_pdf": self._extract_images_from_pdf,
            "generate_bw_variants": self._generate_bw_variants,
            "refine_bw_image": self._refine_bw_image,
            "compute_image_similarity": self._compute_image_similarity,
            "get_image_metadata": self._get_image_metadata,
            "render_pdf_pages": self._render_pdf_pages,
            "analyze_pdf_figures": self._analyze_pdf_figures,
            "crop_region": self._crop_region,
            "create_footprint_json": self._create_footprint_json,
        }

        handler = handlers.get(name)
        if not handler:
            return [TextContent(
                type="text",
                text=serialize_result({"status": "error", "error": f"Unknown tool: {name}"})
            )]

        return await handler(arguments)

    @tool_handler
    async def _extract_images_from_pdf(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Extract images from a PDF file."""
        pdf_path = Path(args["pdf_path"])
        output_dir = Path(args["output_dir"])
        min_size = args.get("min_size_bytes", 5000)

        if not pdf_path.exists():
            return {"status": "error", "error": f"PDF not found: {pdf_path}"}

        output_dir.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_event_loop()

        def extract():
            fitz = _get_fitz()
            images = []
            seen_hashes = set()
            seen_xrefs = set()

            doc = fitz.open(str(pdf_path))

            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    xref = img[0]

                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)

                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        if len(image_bytes) < min_size:
                            continue

                        img_hash = hashlib.md5(image_bytes).hexdigest()
                        if img_hash in seen_hashes:
                            continue
                        seen_hashes.add(img_hash)

                        img_filename = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                        img_path = output_dir / img_filename

                        with open(img_path, "wb") as f:
                            f.write(image_bytes)

                        images.append({
                            "path": str(img_path),
                            "page_num": page_num + 1,
                            "size_bytes": len(image_bytes),
                            "index": len(images)
                        })

                    except Exception as e:
                        logger.warning(f"Could not extract image {img_index} from page {page_num + 1}: {e}")

            doc.close()
            return images

        images = await loop.run_in_executor(_executor, extract)

        return {
            "status": "success",
            "pdf_path": str(pdf_path),
            "output_dir": str(output_dir),
            "images": images,
            "count": len(images)
        }


    @tool_handler
    async def _generate_bw_variants(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate B&W variants using Gemini."""
        image_path = Path(args["image_path"])
        output_dir = Path(args["output_dir"])
        num_variants = args.get("num_variants", 5)

        if not image_path.exists():
            return {"status": "error", "error": f"Image not found: {image_path}"}

        output_dir.mkdir(parents=True, exist_ok=True)
        variants_dir = output_dir / "bw_variants"
        variants_dir.mkdir(exist_ok=True)

        loop = asyncio.get_event_loop()

        def generate_variant(idx: int) -> Optional[str]:
            genai = _get_genai()
            from google.genai import types
            Image = _get_pil()

            client = self._get_gemini_client()

            with open(image_path, "rb") as f:
                image_bytes = f.read()

            ext = image_path.suffix.lower()
            mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
            mime_type = mime_types.get(ext, "image/png")

            prompt = """Make this image completely black and white. Only the device in black and everything else in white. Get rid of the text and everything else please.

Generate a clean image showing ONLY the device structure/geometry as a black silhouette on a pure white background. Remove all:
- Text and labels
- Axes and scale bars
- Color gradients
- Background elements

The output should be a simple, clean black shape representing the device geometry."""

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

                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        image_data = part.inline_data.data
                        variant_path = variants_dir / f"variant_{idx + 1}.png"
                        img = Image.open(io.BytesIO(image_data))
                        img.save(str(variant_path))
                        return str(variant_path)

            except Exception as e:
                logger.warning(f"Failed to generate variant {idx + 1}: {e}")

            return None

        # Generate variants (could parallelize more, but Gemini has rate limits)
        variants = []
        for i in range(num_variants):
            path = await loop.run_in_executor(_executor, generate_variant, i)
            if path:
                variants.append(path)

        if not variants:
            return {
                "status": "error",
                "error": "No B&W variants could be generated"
            }

        return {
            "status": "success",
            "source_image": str(image_path),
            "variants": variants,
            "count": len(variants)
        }

    @tool_handler
    async def _refine_bw_image(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Refine B&W image with custom instructions."""
        source_path = Path(args["source_image_path"])
        output_dir = Path(args["output_dir"])
        custom_instructions = args["custom_instructions"]
        num_variants = args.get("num_variants", 2)

        if not source_path.exists():
            return {"status": "error", "error": f"Source image not found: {source_path}"}

        output_dir.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_event_loop()

        def refine_variant(idx: int) -> Optional[str]:
            genai = _get_genai()
            from google.genai import types
            Image = _get_pil()

            client = self._get_gemini_client()

            with open(source_path, "rb") as f:
                image_bytes = f.read()

            ext = source_path.suffix.lower()
            mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
            mime_type = mime_types.get(ext, "image/png")

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

                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        image_data = part.inline_data.data
                        variant_path = output_dir / f"refined_{idx + 1}.png"
                        img = Image.open(io.BytesIO(image_data))
                        img.save(str(variant_path))
                        return str(variant_path)

            except Exception as e:
                logger.warning(f"Failed to generate refined variant {idx + 1}: {e}")

            return None

        # Generate refined variants
        variants = []
        for i in range(num_variants):
            path = await loop.run_in_executor(_executor, refine_variant, i)
            if path:
                variants.append(path)

        if not variants:
            return {
                "status": "error",
                "error": "No refined variants could be generated"
            }

        return {
            "status": "success",
            "source_image": str(source_path),
            "instructions": custom_instructions,
            "variants": variants,
            "count": len(variants)
        }

    @tool_handler
    async def _compute_image_similarity(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Compute similarity metrics between two images."""
        img1_path = Path(args["image1_path"])
        img2_path = Path(args["image2_path"])

        if not img1_path.exists():
            return {"status": "error", "error": f"Image not found: {img1_path}"}
        if not img2_path.exists():
            return {"status": "error", "error": f"Image not found: {img2_path}"}

        loop = asyncio.get_event_loop()

        def compute():
            Image = _get_pil()
            metrics = _get_skimage_metrics()
            import numpy as np

            # Load and convert to grayscale
            img1 = Image.open(img1_path).convert("L")
            img2 = Image.open(img2_path).convert("L")

            # Resize to same dimensions if needed
            if img1.size != img2.size:
                # Resize smaller to match larger
                target_size = (
                    max(img1.size[0], img2.size[0]),
                    max(img1.size[1], img2.size[1])
                )
                img1 = img1.resize(target_size, Image.LANCZOS)
                img2 = img2.resize(target_size, Image.LANCZOS)

            arr1 = np.array(img1)
            arr2 = np.array(img2)

            # Compute SSIM
            ssim = metrics.structural_similarity(arr1, arr2)

            # Compute MSE
            mse = np.mean((arr1.astype(float) - arr2.astype(float)) ** 2)

            # Compute normalized cross-correlation
            arr1_norm = (arr1 - arr1.mean()) / (arr1.std() + 1e-8)
            arr2_norm = (arr2 - arr2.mean()) / (arr2.std() + 1e-8)
            ncc = np.mean(arr1_norm * arr2_norm)

            return {
                "ssim": float(ssim),
                "mse": float(mse),
                "ncc": float(ncc),
                "image1_size": list(img1.size),
                "image2_size": list(img2.size)
            }

        result = await loop.run_in_executor(_executor, compute)

        return {
            "status": "success",
            "image1": str(img1_path),
            "image2": str(img2_path),
            **result
        }

    @tool_handler
    async def _get_image_metadata(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get metadata about an image file."""
        image_path = Path(args["image_path"])

        if not image_path.exists():
            return {"status": "error", "error": f"Image not found: {image_path}"}

        loop = asyncio.get_event_loop()

        def get_metadata():
            Image = _get_pil()
            import numpy as np

            img = Image.open(image_path)
            arr = np.array(img)

            metadata = {
                "path": str(image_path),
                "width": img.size[0],
                "height": img.size[1],
                "format": img.format,
                "mode": img.mode,
                "file_size_bytes": image_path.stat().st_size,
            }

            # Add histogram info for grayscale analysis
            if img.mode in ["L", "RGB", "RGBA"]:
                gray = img.convert("L")
                gray_arr = np.array(gray)
                metadata["mean_intensity"] = float(gray_arr.mean())
                metadata["std_intensity"] = float(gray_arr.std())
                metadata["min_intensity"] = int(gray_arr.min())
                metadata["max_intensity"] = int(gray_arr.max())

            return metadata

        result = await loop.run_in_executor(_executor, get_metadata)

        return {
            "status": "success",
            **result
        }


    @tool_handler
    async def _analyze_pdf_figures(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Per-page figure diagnostic (keyless). Wraps homi.paper_processing."""
        from homi import paper_processing
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(
            _executor, paper_processing.analyze_pdf_figures, args["pdf_path"]
        )
        return {"status": "success", **report}

    @tool_handler
    async def _crop_region(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic crop from an agent-supplied bbox (keyless)."""
        from homi import paper_processing
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: paper_processing.crop_region(
                args["page_image_path"], args["bbox"], args["output_path"],
                args.get("pad_frac", 0.0),
            ),
        )
        return {"status": "success", **result}

    @tool_handler
    async def _render_pdf_pages(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Render PDF pages as images to capture vector graphics."""
        pdf_path = Path(args["pdf_path"])
        output_dir = Path(args["output_dir"])
        pages = args.get("pages")  # 1-indexed page numbers
        scale = args.get("scale", 2.0)

        if not pdf_path.exists():
            return {"status": "error", "error": f"PDF not found: {pdf_path}"}

        output_dir.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_event_loop()

        def render():
            fitz = _get_fitz()
            doc = fitz.open(str(pdf_path))
            total_pages = len(doc)

            # Default to first 5 pages if not specified
            if pages is None:
                page_nums = list(range(min(5, total_pages)))
            else:
                # Convert 1-indexed to 0-indexed
                page_nums = [p - 1 for p in pages if 0 < p <= total_pages]

            rendered = []
            matrix = fitz.Matrix(scale, scale)

            for page_num in page_nums:
                page = doc[page_num]
                pix = page.get_pixmap(matrix=matrix)
                output_path = output_dir / f"page_{page_num + 1}.png"
                pix.save(str(output_path))
                rendered.append({
                    "path": str(output_path),
                    "page_num": page_num + 1,
                    "width": pix.width,
                    "height": pix.height
                })

            doc.close()
            return rendered, total_pages

        rendered, total_pages = await loop.run_in_executor(_executor, render)

        return {
            "status": "success",
            "pdf_path": str(pdf_path),
            "output_dir": str(output_dir),
            "rendered_pages": rendered,
            "count": len(rendered),
            "total_pages": total_pages
        }




    @tool_handler
    async def _create_footprint_json(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create footprint.json file."""
        length_um = args["length_um"]
        width_um = args["width_um"]
        output_path = Path(args["output_path"])

        # Validate dimensions
        if length_um <= 0 or width_um <= 0:
            return {"status": "error", "error": "Dimensions must be positive"}

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_event_loop()

        def create():
            from homi.footprint_extraction import create_footprint_json
            return create_footprint_json(length_um, width_um, str(output_path))

        result_path = await loop.run_in_executor(_executor, create)

        return {
            "status": "success",
            "output_path": result_path,
            "footprint": {
                "length_um": length_um,
                "width_um": width_um
            }
        }


# Entry point
async def main():
    logging.basicConfig(level=logging.INFO)
    server = MJServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
