"""
HOMI - Paper to GDS Pipeline

A unified system for converting research papers into GDS device representations.

Submodules are imported lazily (PEP 562): importing the ``homi`` package pulls in
no heavy or optional dependencies. Each integration module loads on first access,
so lightweight entry points (e.g. ``homi.anu_artifact``) work without the PDF
extraction or FDTD simulation stacks installed. Access still works exactly as
before — ``from homi import gds_generation`` and ``homi.gds_generation`` both
trigger the import on demand.
"""
import importlib

__version__ = "0.1.0"

_SUBMODULES = frozenset(
    {
        "paper_processing",
        "footprint_extraction",
        "gds_generation",
        "projects",
        "weber_integration",
        "visualization",
        "explorer_ui",
        "flex_integration",
        "simulation_ui",
        "theme",
        "viewer_3d",
        "webgl_viewer",
    }
)


def __getattr__(name):
    if name in _SUBMODULES:
        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module  # cache so subsequent access is a plain attribute
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | _SUBMODULES)
