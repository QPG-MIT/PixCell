"""Identity of the committed candidate-sandbox build specification."""

from __future__ import annotations

import hashlib
from pathlib import Path


SANDBOX_SPEC_LABEL = "org.qpg-mit.pixcell.sandbox-spec-sha256"


def sandbox_spec_sha256() -> str:
    """Hash every input that defines the evaluator image.

    The label lets launch preflight reject an immutable image that was built
    from a different checkout or from an unrelated Dockerfile.
    """

    common_root = Path(__file__).resolve().parent
    sandbox_root = common_root / "sandbox"
    inputs = (
        ("Dockerfile", sandbox_root / "Dockerfile"),
        ("requirements.txt", sandbox_root / "requirements.txt"),
        ("supervise.py", sandbox_root / "supervise.py"),
        ("execute.py", common_root / "execute.py"),
    )
    digest = hashlib.sha256()
    for name, path in inputs:
        payload = path.read_bytes()
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()
