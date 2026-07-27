#!/usr/bin/env python3
"""Regenerate data/BINARY_MANIFEST.json — the checksum manifest for binary
evidence that is kept out of git (raw FDTD hdf5, render PNGs) and shipped as
the external artifact bundle instead (see RELEASING.md).

Run from anywhere: python data/make_binary_manifest.py
"""
import hashlib
import json
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

manifest = {
    "_purpose": (
        "Checksum manifest for local-only binary evidence excluded from git "
        "(distributed as the external artifact bundle alongside the release). "
        "Regenerate: data/make_binary_manifest.py"
    ),
    "_generated": date.today().isoformat(),
    "hdf5": [],
    "png_classes": [],
}

for p in sorted(REPO.glob("data/agents/**/*.hdf5")):
    manifest["hdf5"].append({
        "path": str(p.relative_to(REPO)),
        "bytes": p.stat().st_size,
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
    })


def png_class(label: str, root: Path, pattern: str) -> None:
    files = sorted(root.glob(pattern))
    manifest["png_classes"].append({
        "class": label,
        "root": str(root.relative_to(REPO)),
        "pattern": pattern,
        "files": len(files),
        "bytes": sum(f.stat().st_size for f in files),
    })


png_class("campaign render PNGs (diff/overlay/raster/component under output/)",
          REPO / "data/agents", "**/output/**/*.png")
for i in range(2, 9):
    png_class(f"June trajectory rasters FINAL_{i}",
              REPO / f"data/chatbots/trajectories/FINAL_{i}", "**/*.png")

out = REPO / "data/BINARY_MANIFEST.json"

# The manifest is the integrity record for binary evidence deliberately kept
# OUT of git (raw FDTD hdf5, render PNGs). A tree without those externals —
# any fresh clone — must not silently rewrite the record with the subset it
# happens to see.
if out.exists():
    import sys

    prior = json.loads(out.read_text())
    prior_n = len(prior.get("hdf5", [])) + sum(
        c.get("files", 0) for c in prior.get("png_classes", [])
    )
    new_n = len(manifest["hdf5"]) + sum(c["files"] for c in manifest["png_classes"])
    if new_n < prior_n and "--force" not in sys.argv:
        sys.exit(
            f"refusing: would shrink the manifest {prior_n} -> {new_n} entries "
            "(the external binaries live outside this tree by design); "
            "run with --force only from a tree that holds them"
        )
out.write_text(json.dumps(manifest, indent=1))
print(f"wrote {out}: {len(manifest['hdf5'])} hdf5 hashed, "
      f"{sum(c['files'] for c in manifest['png_classes'])} PNGs summarized")
