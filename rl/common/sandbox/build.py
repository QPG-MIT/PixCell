#!/usr/bin/env python3
"""Build the local candidate sandbox and print its immutable image binding."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    repo_root = root.parents[2]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "src"))
    from rl.common.sandbox_spec import sandbox_spec_sha256

    spec_sha256 = sandbox_spec_sha256()
    tag = "pixcell-evaluator:local"
    subprocess.run(
        [
            "docker",
            "build",
            "--provenance=false",
            "--build-arg",
            f"PIXCELL_SANDBOX_SPEC_SHA256={spec_sha256}",
            "--tag",
            tag,
            str(root),
        ],
        check=True,
    )
    output = subprocess.check_output(
        ["docker", "image", "inspect", tag],
        text=True,
    )
    document = json.loads(output)
    image_id = str(document[0]["Id"])
    if not image_id.startswith("sha256:") or len(image_id) != 71:
        raise RuntimeError("Docker did not return an immutable SHA-256 image ID")
    labels = document[0].get("Config", {}).get("Labels") or {}
    if labels.get("org.qpg-mit.pixcell.sandbox-spec-sha256") != spec_sha256:
        raise RuntimeError("Docker image is missing the committed sandbox identity")
    print(f"export PIXCELL_EVALUATOR_IMAGE={image_id}")


if __name__ == "__main__":
    main()
