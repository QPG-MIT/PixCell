"""Friendly gates for optional-extra imports.

The distribution splits heavy optional stacks into extras (tidy3d lives in
``pixcell[simulate]``). Anything that needs one imports it through here so a
missing extra surfaces as the exact install command, never a raw
ModuleNotFoundError from deep inside a solver.
"""

SIMULATE_REMEDY = "pip install 'pixcell[simulate]'"


def require_tidy3d():
    """Import and return ``tidy3d``, or raise with the simulate-extra remedy."""
    try:
        import tidy3d
    except ImportError as e:
        raise RuntimeError(
            f"tidy3d is not installed — this needs the simulate extra: {SIMULATE_REMEDY}"
        ) from e
    return tidy3d
