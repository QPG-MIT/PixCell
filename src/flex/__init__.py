"""
Flex - Tidy3D FDTD Simulation Module for HOMI

Provides FDTD simulation capabilities using Tidy3D cloud service.
Converts GDSFactory components to 3D simulations and uploads to cloud.

Now with PDK integration for foundry-aware simulations with proper
sidewall angles, rib/slab structures, and anisotropic materials.
"""

__version__ = "0.2.0"

from .core import materials, gds_converter, simulation, cloud, pdk_integration

# PDK-aware simulation functions
from .core.pdk_integration import (
    create_pdk_simulation,
    create_1x2_splitter_simulation,
)
