"""
Drawing Processing Module

Processes hand-drawn sketches of photonic devices and converts them to B&W representations
suitable for Michaelangelo GDS generation.

This is an alternate entry point to the paper pipeline - drawings go directly to B&W
generation without the image extraction/scoring steps needed for papers.
"""

import io
import json
import os
from pathlib import Path
from typing import Callable, Optional

try:
    from PIL import Image
    from google import genai
    from google.genai import types
except ImportError as e:
    raise ImportError(f"Missing dependency: {e}. Run: pip install -r requirements.txt")


def get_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    """Get Gemini client with API key from env or parameter."""
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


# Typical footprint ranges for different device types (for UI suggestions)
TYPICAL_FOOTPRINT_RANGES = {
    "directional_coupler": {"length": (20, 100), "width": (5, 20)},
    "ring_resonator": {"length": (10, 100), "width": (10, 100)},
    "mmi_1x2": {"length": (10, 50), "width": (5, 15)},
    "mmi_2x2": {"length": (15, 60), "width": (8, 20)},
    "y_splitter": {"length": (10, 50), "width": (5, 30)},
    "y_junction": {"length": (10, 50), "width": (5, 30)},
    "waveguide_crossing": {"length": (5, 20), "width": (5, 20)},
    "taper": {"length": (5, 50), "width": (2, 10)},
    "grating_coupler": {"length": (10, 30), "width": (10, 20)},
    "unknown": {"length": (10, 100), "width": (5, 50)},
}


def interpret_drawing(
    image_path: str,
    client: genai.Client = None,
) -> dict:
    """
    Stage 1: Analyze a hand-drawn sketch to understand device type and geometry.

    Args:
        image_path: Path to the drawing image
        client: Gemini client (created if not provided)

    Returns:
        dict with:
        - device_type: Identified device type
        - confidence: high/medium/low
        - drawing_quality: rough/moderate/detailed
        - core_geometry_description: Description of the device geometry
        - required_primitives: List of GDSFactory primitives needed
    """
    if client is None:
        client = get_gemini_client()

    # Load the drawing
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    mime_type = get_image_mime_type(image_path)

    prompt = """You are analyzing a HAND-DRAWN SKETCH of a photonic device. This is NOT a
photograph or simulation - it's a clean sketch drawn by a human.

CLASSIFICATION TASK:
1. What TYPE of photonic device is this? (directional coupler, ring resonator,
   MMI, Y-splitter, waveguide crossing, taper, grating coupler, etc.)
2. What is the QUALITY of the drawing? (rough sketch / moderate / detailed)
3. What are the KEY GEOMETRIC FEATURES? Describe the shapes, their arrangement,
   and how they connect.
4. What GDSFactory PRIMITIVES would be needed to recreate this device?

Common GDSFactory primitives:
- gf.components.straight (straight waveguide)
- gf.components.bend_euler (smooth bend)
- gf.components.bend_circular (circular arc bend)
- gf.components.coupler (directional coupler)
- gf.components.ring (ring resonator)
- gf.components.mmi1x2, gf.components.mmi2x2 (MMI couplers)
- gf.components.taper (width taper)
- gf.components.crossing (waveguide crossing)

Respond with ONLY a JSON object:
{
    "device_type": "<identified device type>",
    "confidence": "<high|medium|low>",
    "drawing_quality": "<rough|moderate|detailed>",
    "core_geometry_description": "<detailed description of the geometry>",
    "required_primitives": ["gf.components.xxx", "gf.components.yyy", ...]
}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            ],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="high")
            )
        )
        response_text = response.text.strip()

        # Parse JSON from response
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        result = json.loads(response_text)

        # Normalize device_type for footprint lookup
        device_type = result.get("device_type", "unknown").lower().replace(" ", "_")
        result["device_type_normalized"] = device_type

        # Add suggested footprint range
        footprint_range = TYPICAL_FOOTPRINT_RANGES.get(
            device_type,
            TYPICAL_FOOTPRINT_RANGES["unknown"]
        )
        result["suggested_footprint_range"] = footprint_range

        return result

    except json.JSONDecodeError as e:
        return {
            "device_type": "unknown",
            "confidence": "low",
            "drawing_quality": "unknown",
            "core_geometry_description": "Failed to parse interpretation",
            "required_primitives": [],
            "error": f"JSON parse error: {e}",
            "raw_response": response_text if 'response_text' in locals() else None
        }
    except Exception as e:
        return {
            "device_type": "unknown",
            "confidence": "low",
            "drawing_quality": "unknown",
            "core_geometry_description": "Interpretation failed",
            "required_primitives": [],
            "error": str(e)
        }


def generate_drawing_bw_variants(
    image_path: str,
    client: genai.Client = None,
    output_dir: str = None,
    num_variants: int = 5,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> list[str]:
    """
    Generate clean B&W silhouettes from a hand-drawn sketch.

    Args:
        image_path: Path to the drawing image
        client: Gemini client (created if not provided)
        output_dir: Directory to save variants (uses temp dir if not provided)
        num_variants: Number of variants to generate
        progress_callback: Optional callback(current, total) for progress

    Returns:
        List of paths to generated B&W variant images
    """
    if client is None:
        client = get_gemini_client()

    if output_dir is None:
        output_dir = Path(image_path).parent / "bw_variants"
    os.makedirs(output_dir, exist_ok=True)

    # Load the drawing
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    mime_type = get_image_mime_type(image_path)

    # Simple B&W generation prompt
    prompt = """Convert this hand-drawn sketch into a clean B&W silhouette.

Output: BLACK silhouette on PURE WHITE background.

Guidelines:
- Straighten wobbly lines
- Smooth curves
- Preserve the drawn proportions (waveguides are drawn as boxes, not lines)
- Remove pencil/pen texture and background
- Enforce symmetry where it appears intended
- Maintain uniform widths where drawn uniform

The output should be a clean, manufacturing-ready silhouette."""

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


def _get_device_specific_rules(device_type: str) -> str:
    """Get device-specific regularization rules for the B&W generation prompt."""
    device_type = device_type.lower().replace(" ", "_")

    rules = {
        "directional_coupler": """
- Two parallel waveguides in the coupling region with UNIFORM gap
- S-bends or Euler bends for port separation should be SMOOTH
- Symmetric top/bottom waveguides (mirror symmetry)
- Input and output ports should be aligned horizontally
""",
        "ring_resonator": """
- Ring should be a PERFECT circle or racetrack shape
- Bus waveguide(s) running tangent to the ring
- Uniform coupling gap between ring and bus
- Ring should be a closed loop with uniform width
""",
        "mmi_1x2": """
- Rectangular multimode region with STRAIGHT edges
- Single input waveguide centered on one end
- Two output waveguides symmetrically placed on the other end
- Tapers at waveguide-MMI junctions should be smooth
""",
        "mmi_2x2": """
- Rectangular multimode region with STRAIGHT edges
- Two input waveguides symmetrically placed
- Two output waveguides symmetrically placed
- All tapers should be identical and smooth
""",
        "y_splitter": """
- Single input waveguide
- Two output waveguides at SYMMETRIC angles
- Smooth junction region (no sharp corners)
- Equal arm lengths if symmetric design
""",
        "y_junction": """
- Single input waveguide
- Two output waveguides at SYMMETRIC angles
- Smooth junction region (no sharp corners)
- Equal arm lengths if symmetric design
""",
        "waveguide_crossing": """
- Two waveguides crossing at right angles (90 degrees)
- Crossing region may have elliptical widening
- Symmetric in both axes
""",
        "taper": """
- Smooth transition between two widths
- Linear or adiabatic taper profile
- No abrupt width changes
""",
        "grating_coupler": """
- Regular periodic grating pattern
- Consistent grating period and fill factor
- Taper region connecting to waveguide
""",
    }

    return rules.get(device_type, """
- Follow standard photonic design rules
- Maintain uniform waveguide widths
- Ensure smooth transitions and bends
""")


def process_drawing(
    image_path: str,
    output_dir: str,
    client: genai.Client = None,
    num_bw_variants: int = 5,
    progress_callback: Optional[Callable[[str], None]] = None
) -> dict:
    """
    Full drawing processing pipeline: interpret + generate B&W variants.

    Args:
        image_path: Path to the drawing image
        output_dir: Directory to save all outputs
        client: Gemini client (created if not provided)
        num_bw_variants: Number of B&W variants to generate
        progress_callback: Optional callback(status_message) for progress

    Returns:
        dict with:
        - interpretation: Result from interpret_drawing()
        - bw_variants: List of paths to B&W variant images
        - original_drawing: Path to original drawing (copied to output_dir)
    """
    if client is None:
        client = get_gemini_client()

    os.makedirs(output_dir, exist_ok=True)

    # Copy original drawing to output directory
    original_filename = Path(image_path).name
    original_dest = os.path.join(output_dir, f"original_{original_filename}")
    img = Image.open(image_path)
    img.save(original_dest)

    # Stage 1: Interpret drawing
    if progress_callback:
        progress_callback("Interpreting drawing...")

    interpretation = interpret_drawing(image_path, client)

    # Save interpretation
    interpretation_path = os.path.join(output_dir, "interpretation.json")
    with open(interpretation_path, "w") as f:
        json.dump(interpretation, f, indent=2)

    # Stage 2: Generate B&W variants
    if progress_callback:
        progress_callback("Generating B&W variants...")

    bw_variants_dir = os.path.join(output_dir, "bw_variants")

    def bw_progress(current, total):
        if progress_callback:
            progress_callback(f"Generating B&W variant {current}/{total}...")

    bw_variants = generate_drawing_bw_variants(
        image_path,
        interpretation,
        client,
        bw_variants_dir,
        num_bw_variants,
        bw_progress
    )

    return {
        "interpretation": interpretation,
        "bw_variants": bw_variants,
        "original_drawing": original_dest,
        "interpretation_path": interpretation_path
    }


def create_michaelangelo_output(
    selected_bw_path: str,
    interpretation: dict,
    footprint_um: tuple[float, float],
    output_dir: str
) -> dict:
    """
    Prepare all files needed for Michaelangelo from a processed drawing.

    Args:
        selected_bw_path: Path to the selected B&W variant
        interpretation: Result from interpret_drawing()
        footprint_um: (length_um, width_um) from user input
        output_dir: Directory to save Michaelangelo-ready files

    Returns:
        dict with paths to all created files
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. Copy B&W image as component.png
    component_path = os.path.join(output_dir, "component.png")
    img = Image.open(selected_bw_path)
    img.save(component_path)

    # 2. Create footprint.json
    footprint_path = os.path.join(output_dir, "footprint.json")
    footprint_data = {"footprint_um": list(footprint_um)}
    with open(footprint_path, "w") as f:
        json.dump(footprint_data, f, indent=2)

    # 3. Create drawing-specific prompt.md
    prompt_path = os.path.join(output_dir, "prompt.md")
    prompt_content = _create_drawing_prompt(interpretation, footprint_um)
    with open(prompt_path, "w") as f:
        f.write(prompt_content)

    # 4. Save full metadata
    metadata_path = os.path.join(output_dir, "drawing_metadata.json")
    metadata = {
        "source": "drawing",
        "interpretation": interpretation,
        "footprint_um": list(footprint_um),
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return {
        "component_png": component_path,
        "footprint_json": footprint_path,
        "prompt_md": prompt_path,
        "metadata_json": metadata_path
    }


def _create_drawing_prompt(interpretation: dict, footprint_um: tuple[float, float]) -> str:
    """Create drawing-specific prompt for Michaelangelo."""
    device_type = interpretation.get("device_type", "unknown device")
    geometry_desc = interpretation.get("core_geometry_description", "")
    primitives = interpretation.get("required_primitives", [])

    prompt = f"""Study the device in the attached PNG. This image was generated from a
HAND-DRAWN SKETCH and has been regularized to show clean geometry.

## Device Analysis
Type: {device_type}
Key features: {geometry_desc}

## Recommended Primitives
{chr(10).join(f"- {p}" for p in primitives) if primitives else "- Use appropriate gdsfactory components"}

## Footprint
{footprint_um[0]} um x {footprint_um[1]} um

Since this is from a sketch:
- Trust the topology (what connects to what)
- The waveguide widths are EXPLICITLY DRAWN as boxes - preserve the proportions shown
- Make smooth curves using Euler bends where appropriate
- Enforce symmetry where the design appears symmetric
- Scale the design to match the footprint while maintaining proportions

Recreate this device using GDSFactory parametric functions. Write the Python script
that generates a gf.Component matching this geometry within the specified footprint.
"""
    return prompt
