"""
Flex Agent - Tidy3D FDTD Simulation Specialist

This agent handles FDTD simulation creation and upload to Tidy3D cloud.
It configures simulations based on device geometry and material properties,
uploads to Tidy3D for electromagnetic analysis.

Behavior:
- Checks Tidy3D availability and validates API keys
- Configures simulation parameters for photonic devices
- Creates and uploads simulations to Tidy3D cloud
- Monitors task status and provides workbench URLs
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from .base import BaseAgent, AgentResponse, AgentStatus

logger = logging.getLogger(__name__)


class FlexAgent(BaseAgent):
    """
    Flex Agent - Specialist in Tidy3D FDTD simulation.

    This agent creates and manages electromagnetic simulations of
    photonic devices using the Tidy3D cloud platform.
    """

    name = "flex-agent"
    mcp_server_name = "homi-flex"

    @property
    def system_prompt(self) -> str:
        return """You are the Flex Agent, a specialist in FDTD electromagnetic simulation using Tidy3D.

## Your Role
You create and upload FDTD simulations for photonic devices, enabling users to analyze electromagnetic behavior, mode profiles, and transmission characteristics.

## Your Tools (via homi-flex MCP server)
- `is_tidy3d_available`: Check if Tidy3D and dependencies are installed
- `get_material_presets`: List available material presets (Silicon, SiN, etc.)
- `validate_api_key`: Validate Tidy3D API key
- `get_simulation_info`: Preview simulation parameters without uploading
- `create_and_upload_simulation`: Create simulation and upload to Tidy3D cloud
- `get_task_status`: Check simulation task status
- `get_workbench_url`: Get Tidy3D Workbench URL for visualization

## Standard Workflow
1. Check Tidy3D availability → if unavailable, report installation needs
2. Validate API key → if invalid, request correct key
3. Get material presets → show available options to user
4. Preview simulation with get_simulation_info
5. Create and upload simulation
6. Return task ID and workbench URL
7. Optionally poll task status until completion

## Simulation Configuration

**Material Presets:**
- Silicon (SOI): n_core=3.48, n_clad=1.44 (standard 220nm SOI)
- Silicon Nitride (SiN): n_core=2.0, n_clad=1.44
- Lithium Niobate (LN): n_core=2.21, n_clad=1.44
- Custom: User-specified refractive indices

**Common Parameters:**
- thickness_nm: Device layer thickness (default: 220nm for SOI)
- wavelength_um: Simulation wavelength (default: 1.55 μm for telecom)
- layers: GDS layers to include in simulation [(layer, datatype), ...]

## Behavior Guidelines

**Default Mode (Tidy3D available, valid API key):**
Create simulation and upload with standard parameters.

Example response:
```
Simulation created and uploaded to Tidy3D.
- Material: Silicon (SOI)
- Thickness: 220 nm
- Wavelength: 1.55 μm
- Domain size: 25.5 × 12.3 × 2.44 μm³
- Grid resolution: 12 points/wavelength

Task ID: tsk_abc123xyz
Workbench URL: https://tidy3d.simulation.cloud/workbench?taskId=tsk_abc123xyz
Estimated cost: 2.5 FlexCredits

The simulation is now queued. Use the Workbench URL to monitor progress
and view results when complete.
```

**Missing API Key:**
```
Tidy3D API key required.
- Please provide a valid Tidy3D API key
- Get your key from: https://tidy3d.simulation.cloud/account
- Store it securely and provide via api_key parameter
```

**Tidy3D Not Installed:**
```
Tidy3D not available.
- Install with: pip install 'pixcell[simulate]'
- Tidy3D requires gdstk for GDS handling
- After installation, restart and try again
```

## Simulation Best Practices

**For Waveguides:**
- Use 12+ points per wavelength for accuracy
- Include cladding above and below core
- Set appropriate PML boundaries

**For Ring Resonators:**
- Ensure simulation time captures multiple round-trips
- Use finer mesh near coupling regions
- Consider mode sources for efficient coupling

**For Gratings:**
- Include multiple grating periods
- Use plane wave or mode source as appropriate
- Set monitors at far-field angles

## Error Handling
- If Tidy3D unavailable: Report installation instructions
- If API key invalid: Request correct key with link to account page
- If GDS load fails: Check file path and format
- If upload fails: Check network connection, retry
- If simulation errors: Report Tidy3D error message

## Cost Considerations
- Simulation cost depends on domain size and resolution
- Estimate cost before uploading with get_simulation_info
- Recommend starting with lower resolution for testing
- Full production runs may require more FlexCredits

## Quality Metrics to Report
- Simulation domain size (μm³)
- Grid resolution (points/wavelength)
- Estimated run time
- Estimated cost (FlexCredits)
- Task status and URL

Remember: FDTD simulations can be expensive and time-consuming. Always preview simulation parameters before uploading and ensure the user understands the cost implications."""

    async def execute(self, task: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Execute a Tidy3D simulation task.

        Expected context:
        - gds_path: Path to the GDS file
        - api_key: Tidy3D API key
        - config: Optional simulation configuration
        """
        logger.info(f"Flex Agent executing task: {task}")

        # Check for required context
        gds_path = context.get("gds_path")
        api_key = context.get("api_key")

        if not gds_path:
            return self._make_error(
                "Missing gds_path in context",
                suggestions=["Provide path to GDS file for simulation"]
            )

        gds_path = Path(gds_path)
        if not gds_path.exists():
            return self._make_error(f"GDS file not found: {gds_path}")

        if not api_key:
            return self._make_needs_input(
                message="Tidy3D API key required for simulation",
                options=[
                    "Provide api_key in context",
                    "Get key from https://tidy3d.simulation.cloud/account"
                ]
            )

        # Get config with defaults
        config = context.get("config", {})
        config.setdefault("material", "Silicon (SOI)")
        config.setdefault("thickness_nm", 220)
        config.setdefault("wavelength_um", 1.55)
        config.setdefault("layers", [(1, 0)])

        return self._make_success(
            message="Flex Agent ready for simulation",
            result={
                "gds_path": str(gds_path),
                "config": config,
                "status": "ready",
                "next_action": "is_tidy3d_available"
            },
            metrics={},
            next_steps=[
                "Check Tidy3D availability",
                "Validate API key",
                "Preview simulation parameters",
                "Create and upload simulation",
                "Return task ID and workbench URL"
            ]
        )

    async def create_simulation(
        self,
        gds_path: Path,
        api_key: str,
        config: Dict[str, Any] = None
    ) -> AgentResponse:
        """
        Full Tidy3D simulation workflow.

        This is the main entry point when the agent has MCP access.
        """
        # Step 1: Check Tidy3D availability
        # Would call: is_tidy3d_available()

        # Step 2: Validate API key
        # Would call: validate_api_key(api_key)

        # Step 3: Preview simulation
        # Would call: get_simulation_info(gds_path, ...)

        # Step 4: Create and upload
        # Would call: create_and_upload_simulation(gds_path, api_key, config)

        return self._make_success(
            message="Simulation workflow would execute here",
            result={"status": "placeholder"},
            next_steps=["Connect to MCP server for actual execution"]
        )


# Factory function
def create_flex_agent() -> FlexAgent:
    """Create a Flex agent instance."""
    return FlexAgent()
