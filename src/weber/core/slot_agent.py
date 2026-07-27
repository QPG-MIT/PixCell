"""
Weber Slot Agent

Uses Claude API to analyze GDSFactory scripts and generate semantic slot configurations.
The agent understands device topology and groups components into logical slots.
"""

import json
import hashlib
from pathlib import Path
from typing import Optional
from dataclasses import asdict

from .analyzer import ScriptAnalysis
from .default_slots import SlotConfig, SlotDefinition, LayerGroup, GlobalParameter, SlotParameter
from .config import CACHE_DIR, get_anthropic_api_key

# System prompt for the slot agent
SLOT_AGENT_SYSTEM_PROMPT = """You are analyzing a GDSFactory photonic device script to enable interactive exploration.

Your task is to analyze the script and its extracted components to create a slot configuration that allows users to:
1. Swap between compatible component types
2. Adjust parameters with sliders
3. Assign components to different GDS layers

## Your Analysis Tasks:

### 1. GROUPING
Identify logical parts of the device based on function and position:
- "ring_bends" - bends that form a ring resonator
- "internal_pads" - rectangular pads inside a structure
- "waveguide_arms" - straight waveguide sections
- "connectors" - S-bends or transitions between parts
- etc.

### 2. SLOTS
For each logical group, determine:
- Which components belong to this slot
- What component types can be swapped (e.g., bend_circular ↔ bend_euler)
- What parameters should be exposed as sliders
- Reasonable min/max/step for each parameter

### 3. SWAPPABLE TYPES
Use these mappings for swappable components:
- Basic shapes: rectangle ↔ circle ↔ ellipse ↔ triangle
- Bends: bend_circular ↔ bend_euler ↔ bend_s
- Waveguides: straight ↔ taper

### 4. LAYER GROUPS
Suggest which slots should share layer assignments:
- Outer ring structure → one layer
- Internal MZI/splitter → another layer
- Holes/cutouts → potentially separate layer

### 5. GLOBAL PARAMETERS
Identify parameters that affect multiple components:
- y_arm_offset - vertical offset of internal arms
- gap - spacing between elements
- etc.

## Output Format

Return ONLY valid JSON in this exact format:
```json
{
  "slots": [
    {
      "slot_id": "unique_identifier",
      "display_name": "Human Readable Name",
      "component_ids": ["comp1", "comp2"],
      "current_type": "bend_circular",
      "allowed_types": ["bend_circular", "bend_euler", "bend_s"],
      "category": "ring",
      "parameters": [
        {
          "name": "radius",
          "label": "Radius",
          "min_value": 0.5,
          "max_value": 5.0,
          "default_value": 1.1,
          "step": 0.1,
          "unit": "um"
        }
      ],
      "layer_group": "outer_ring"
    }
  ],
  "layer_groups": [
    {
      "name": "Outer Ring",
      "slot_ids": ["ring_bend_left", "ring_bend_right"],
      "default_layer": [1, 0],
      "color": "#2E86AB"
    }
  ],
  "global_params": [
    {
      "name": "y_arm_offset",
      "label": "Arm Y Offset",
      "affects": ["arm_top", "arm_bottom"],
      "min_value": 0.1,
      "max_value": 1.5,
      "default_value": 0.35,
      "step": 0.05
    }
  ]
}
```

IMPORTANT:
- Return ONLY the JSON, no other text
- Use snake_case for slot_id and parameter names
- Use descriptive display_name values
- Include reasonable ranges based on the values in the script
- Group related components into the same slot when appropriate
"""


class SlotAgent:
    """Claude API agent for semantic analysis of GDSFactory scripts."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the slot agent.

        Args:
            api_key: Anthropic API key. If None, uses environment variable.
        """
        self.api_key = api_key or get_anthropic_api_key()
        self._client = None

    @property
    def client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise RuntimeError(
                    "anthropic package not installed. "
                    "Install with: pip install anthropic"
                )
        return self._client

    def _get_cache_key(self, analysis: ScriptAnalysis, script_source: str) -> str:
        """Generate a cache key from the analysis and source."""
        content = analysis.to_json() + script_source
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Try to get a cached response."""
        cache_file = CACHE_DIR / f"{cache_key}.json"
        if cache_file.exists():
            try:
                return cache_file.read_text()
            except Exception:
                pass
        return None

    def _cache_response(self, cache_key: str, response: str) -> None:
        """Cache a response."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{cache_key}.json"
        try:
            cache_file.write_text(response)
        except Exception:
            pass

    def analyze(
        self,
        analysis: ScriptAnalysis,
        script_source: str,
        use_cache: bool = True
    ) -> SlotConfig:
        """
        Analyze a script and generate slot configuration.

        Args:
            analysis: ScriptAnalysis from the analyzer
            script_source: Original Python source code
            use_cache: Whether to use cached responses

        Returns:
            SlotConfig with AI-generated slot definitions
        """
        if not self.api_key:
            raise ValueError(
                "No API key provided. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key to SlotAgent."
            )

        # Check cache
        cache_key = self._get_cache_key(analysis, script_source)
        if use_cache:
            cached = self._get_cached_response(cache_key)
            if cached:
                return self._parse_response(cached)

        # Build the prompt
        user_message = f"""Please analyze this GDSFactory script and create a slot configuration.

## Extracted Analysis

```json
{analysis.to_json()}
```

## Original Script

```python
{script_source}
```

Based on this analysis, create a comprehensive slot configuration that groups components logically and enables interactive exploration.
"""

        # Call Claude API
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SLOT_AGENT_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": user_message
            }]
        )

        # Extract response text
        response_text = response.content[0].text

        # Cache the response
        if use_cache:
            self._cache_response(cache_key, response_text)

        return self._parse_response(response_text)

    def _parse_response(self, response_text: str) -> SlotConfig:
        """Parse the agent response into a SlotConfig."""
        # Try to extract JSON from the response
        json_text = response_text.strip()

        # Handle markdown code blocks
        if "```json" in json_text:
            start = json_text.find("```json") + 7
            end = json_text.find("```", start)
            json_text = json_text[start:end].strip()
        elif "```" in json_text:
            start = json_text.find("```") + 3
            end = json_text.find("```", start)
            json_text = json_text[start:end].strip()

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse agent response as JSON: {e}\nResponse: {response_text[:500]}")

        # Convert to SlotConfig
        slots = []
        for s in data.get("slots", []):
            parameters = []
            for p in s.get("parameters", []):
                parameters.append(SlotParameter(
                    name=p["name"],
                    label=p.get("label", p["name"].replace("_", " ").title()),
                    min_value=float(p.get("min_value", 0.1)),
                    max_value=float(p.get("max_value", 10.0)),
                    default_value=float(p.get("default_value", 1.0)),
                    step=float(p.get("step", 0.1)),
                    unit=p.get("unit", "um")
                ))

            slots.append(SlotDefinition(
                slot_id=s["slot_id"],
                display_name=s.get("display_name", s["slot_id"]),
                component_ids=s.get("component_ids", [s["slot_id"]]),
                current_type=s.get("current_type", "unknown"),
                allowed_types=s.get("allowed_types", [s.get("current_type", "unknown")]),
                category=s.get("category", "other"),
                parameters=parameters,
                layer_group=s.get("layer_group")
            ))

        layer_groups = []
        for lg in data.get("layer_groups", []):
            default_layer = lg.get("default_layer", [1, 0])
            if isinstance(default_layer, list):
                default_layer = tuple(default_layer)
            layer_groups.append(LayerGroup(
                name=lg["name"],
                slot_ids=lg.get("slot_ids", []),
                default_layer=default_layer,
                color=lg.get("color", "#2E86AB")
            ))

        global_params = []
        for gp in data.get("global_params", []):
            global_params.append(GlobalParameter(
                name=gp["name"],
                label=gp.get("label", gp["name"].replace("_", " ").title()),
                affects=gp.get("affects", []),
                min_value=float(gp.get("min_value", 0.1)),
                max_value=float(gp.get("max_value", 5.0)),
                default_value=float(gp.get("default_value", 1.0)),
                step=float(gp.get("step", 0.1))
            ))

        return SlotConfig(
            slots=slots,
            layer_groups=layer_groups,
            global_params=global_params
        )


def analyze_with_agent(
    script_path: str,
    api_key: Optional[str] = None,
    use_cache: bool = True
) -> SlotConfig:
    """
    Convenience function to analyze a script with the slot agent.

    Args:
        script_path: Path to the GDSFactory script
        api_key: Optional API key
        use_cache: Whether to use cached responses

    Returns:
        SlotConfig from the agent analysis
    """
    from .analyzer import analyze_script

    # Analyze the script
    analysis = analyze_script(script_path)

    # Read source
    script_source = Path(script_path).read_text()

    # Run agent
    agent = SlotAgent(api_key=api_key)
    return agent.analyze(analysis, script_source, use_cache=use_cache)
