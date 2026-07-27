"""
Footprint Extraction Module

Uses Gemini to analyze research papers and extract device dimensions.
"""

import json
import os
import re
from typing import Optional

try:
    import fitz  # PyMuPDF
    from google import genai
    from google.genai import types

    # Load .env (upward search / checkout / ~/.pixcell/env)
    from homi.paths import load_env
    load_env()
except ImportError as e:
    raise ImportError(f"Missing dependency: {e}. Run: ./setup.sh (or `uv sync`)")


def extract_footprint_from_paper(
    pdf_path: str,
    selected_image_path: Optional[str],
    client: genai.Client,
    max_pages: int = 10
) -> dict:
    """
    Use Gemini to analyze a paper and extract device dimensions.

    Args:
        pdf_path: Path to the PDF paper
        selected_image_path: Path to the selected device image (for context)
        client: Gemini client
        max_pages: Maximum number of pages to analyze

    Returns:
        dict with:
        - length_um: Extracted length in microns (or None)
        - width_um: Extracted width in microns (or None)
        - confidence: "high", "medium", or "low"
        - source: Text excerpt where dimensions were found
        - reasoning: Gemini's explanation
    """
    # Extract text from PDF
    doc = fitz.open(pdf_path)
    text_content = []

    for page_num in range(min(len(doc), max_pages)):
        page = doc[page_num]
        text_content.append(f"--- Page {page_num + 1} ---\n{page.get_text()}")

    doc.close()
    full_text = "\n\n".join(text_content)

    # Truncate if too long (keep first ~15000 chars)
    if len(full_text) > 15000:
        full_text = full_text[:15000] + "\n...[truncated]..."

    # Build the prompt
    prompt = f"""Analyze this research paper about a photonic/silicon device and extract the device dimensions.

Look for:
1. Device footprint/size mentioned in text (e.g., "10 μm × 5 μm", "device measures 15 microns")
2. Scale bars in figure captions (e.g., "scale bar: 2 μm")
3. Waveguide/component dimensions (e.g., "waveguide width of 500 nm")
4. Any numerical dimensions with units like μm, nm, microns, or micrometers

Common photonic device dimensions:
- Typical range: 1-100 μm for length/width
- Waveguides: 0.3-2 μm wide
- Ring resonators: 5-50 μm diameter
- Couplers: 1-20 μm long

PAPER TEXT:
{full_text}

Respond with ONLY a JSON object in this exact format:
{{
    "length_um": <number or null>,
    "width_um": <number or null>,
    "confidence": "<high|medium|low>",
    "source": "<exact text excerpt where you found the dimensions>",
    "reasoning": "<brief explanation of how you determined the dimensions>"
}}

If you cannot find clear dimensions, set length_um and width_um to null and explain in reasoning.
If you find only one dimension, estimate the other based on typical aspect ratios for similar devices.
Always convert to micrometers (μm) - e.g., 500 nm = 0.5 μm.
"""

    # Add the selected image for additional context if available
    content_parts = [types.Part.from_text(text=prompt)]

    if selected_image_path and os.path.exists(selected_image_path):
        try:
            with open(selected_image_path, "rb") as f:
                image_bytes = f.read()
            content_parts.insert(0, types.Part.from_text(text="Here is the device image from the paper for reference:"))
            content_parts.insert(1, types.Part.from_bytes(data=image_bytes, mime_type="image/png"))
        except Exception as e:
            print(f"Warning: Could not load selected image: {e}")

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

        # Parse JSON response
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        result = json.loads(response_text)

        # Handle case where Gemini returns a list instead of a dict
        if isinstance(result, list):
            if len(result) > 0 and isinstance(result[0], dict):
                result = result[0]
            else:
                return {
                    "length_um": None,
                    "width_um": None,
                    "confidence": "low",
                    "source": "",
                    "reasoning": "Gemini returned an empty or invalid list",
                    "raw_response": response_text
                }

        # Validate and sanitize the response
        return {
            "length_um": _parse_dimension(result.get("length_um")),
            "width_um": _parse_dimension(result.get("width_um")),
            "confidence": result.get("confidence", "low"),
            "source": result.get("source", ""),
            "reasoning": result.get("reasoning", ""),
            "raw_response": response_text
        }

    except json.JSONDecodeError as e:
        return {
            "length_um": None,
            "width_um": None,
            "confidence": "low",
            "source": "",
            "reasoning": f"Failed to parse Gemini response: {e}",
            "raw_response": response_text if 'response_text' in locals() else None
        }
    except Exception as e:
        return {
            "length_um": None,
            "width_um": None,
            "confidence": "low",
            "source": "",
            "reasoning": f"Error during extraction: {e}",
            "raw_response": response_text if 'response_text' in locals() else None
        }


def _parse_dimension(value) -> Optional[float]:
    """Parse a dimension value, returning float or None."""
    if value is None:
        return None
    try:
        val = float(value)
        # Sanity check: most photonic devices are 0.1-1000 μm
        if 0.01 <= val <= 10000:
            return val
        return None
    except (TypeError, ValueError):
        return None


def extract_dimensions_from_text(text: str) -> list[dict]:
    """
    Extract potential dimensions from text using regex patterns.

    Returns list of dicts with 'value', 'unit', 'context'.
    """
    patterns = [
        # Match "X μm × Y μm" or "X × Y μm"
        r'(\d+(?:\.\d+)?)\s*(?:μm|um|µm|microns?|micrometers?)\s*[×x]\s*(\d+(?:\.\d+)?)\s*(?:μm|um|µm|microns?|micrometers?)?',
        # Match "X nm × Y nm"
        r'(\d+(?:\.\d+)?)\s*nm\s*[×x]\s*(\d+(?:\.\d+)?)\s*nm',
        # Match single dimension "X μm"
        r'(\d+(?:\.\d+)?)\s*(?:μm|um|µm|microns?|micrometers?)',
        # Match single dimension "X nm"
        r'(\d+(?:\.\d+)?)\s*nm',
    ]

    results = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # Get context (30 chars before and after)
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end]

            results.append({
                "match": match.group(0),
                "groups": match.groups(),
                "context": context
            })

    return results


def create_footprint_json(length_um: float, width_um: float, output_path: str) -> str:
    """
    Create a footprint.json file for Michaelangelo.

    Args:
        length_um: Device length in micrometers
        width_um: Device width in micrometers
        output_path: Path to save the JSON file

    Returns:
        Path to the created file
    """
    footprint = {
        "footprint_um": [length_um, width_um]
    }

    with open(output_path, "w") as f:
        json.dump(footprint, f, indent=2)

    return output_path


def get_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    """Get Gemini client with API key from env."""
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Set it in environment or .env file.")
    return genai.Client(api_key=api_key)


