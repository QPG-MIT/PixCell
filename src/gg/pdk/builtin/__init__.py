"""
Builtin PDK Definitions

Pre-parsed PDK definitions for common foundries.
"""

import json
from pathlib import Path
from typing import Dict

from ..schema import PDKDefinition

# Directory containing builtin PDK JSON files
BUILTIN_DIR = Path(__file__).parent


def load_builtin_pdk(name: str) -> PDKDefinition:
    """
    Load a builtin PDK definition by name.

    Args:
        name: PDK name (e.g., "lightium_tfln", "hyperlight_active")

    Returns:
        PDKDefinition object

    Raises:
        FileNotFoundError: If PDK not found
    """
    json_path = BUILTIN_DIR / f"{name}.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Builtin PDK not found: {name}")

    return PDKDefinition.load(json_path)


def list_builtin_pdks() -> Dict[str, str]:
    """
    List all available builtin PDKs.

    Returns:
        Dictionary mapping PDK name to description
    """
    pdks = {}
    for json_file in BUILTIN_DIR.glob("*.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)
                pdks[json_file.stem] = data.get("description", data.get("name", json_file.stem))
        except (json.JSONDecodeError, KeyError):
            continue
    return pdks


# Convenience aliases
LIGHTIUM_TFLN = "lightium_tfln"
HYPERLIGHT_ACTIVE = "hyperlight_active"
GENERIC_SI220 = "generic_si220"
