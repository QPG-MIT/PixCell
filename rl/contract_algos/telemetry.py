"""Publish explicitly selected experiment evidence to the user's W&B project.

The Forge URL is the UI. The existing W&B SaaS API remains api.wandb.ai.
Credentials are read by the SDK, never accepted on the command line.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


ENTITY = "aadarwal-massachusetts-institute-of-technology"
PROJECT = "visual_signal_algorithms"


def scalar_metrics(document: dict, prefix: str = "") -> dict:
    metrics = {}
    for key, value in document.items():
        name = f"{prefix}/{key}" if prefix else key
        if isinstance(value, dict):
            metrics.update(scalar_metrics(value, name))
        elif isinstance(value, (int, float)) and math.isfinite(value):
            metrics[name] = value
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, action="append", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--kind", choices=["preflight", "inference-probe", "signal-audit", "optimizer-smoke"], required=True)
    parser.add_argument("--dir", type=Path, default=Path(".contract-algos/wandb"))
    args = parser.parse_args()
    reports = [p.resolve(strict=True) for p in args.report]
    if len({p.name for p in reports}) != len(reports):
        parser.error("report filenames must be unique")
    documents = {}
    for path in reports:
        if path.suffix != ".json":
            parser.error("only explicit JSON reports are accepted")
        documents[path.name] = json.loads(path.read_text())
    training_performed = args.kind == "optimizer-smoke" and any(
        document.get("status") == "passed" and document.get("optimizer_steps", 0) > 0
        for document in documents.values()
    )
    if args.kind == "optimizer-smoke" and not training_performed:
        parser.error("optimizer-smoke requires a passed result with positive optimizer_steps")
    if args.kind == "optimizer-smoke" and not any(
        document.get("model_path") and document.get("snapshot_revision")
        and document.get("script_sha256") for document in documents.values()
    ):
        parser.error("optimizer-smoke also requires its model/revision/script config.json")
    import wandb

    args.dir.mkdir(parents=True, exist_ok=True)
    with wandb.init(
        entity=ENTITY, project=PROJECT, name=args.name, job_type=args.kind,
        dir=str(args.dir), config={"training_performed": training_performed, "evidence_kind": args.kind},
        settings=wandb.Settings(disable_git=True),
    ) as run:
        artifact = wandb.Artifact(f"{run.id}-evidence", type="experiment-evidence")
        for path in reports:
            artifact.add_file(str(path), name=path.name)
        run.log_artifact(artifact)
        run.summary["training_performed"] = training_performed
        run.summary["evidence_kind"] = args.kind
        run.summary["evidence_files"] = [p.name for p in reports]
        for filename, document in documents.items():
            # Summary/result scalars are metrics; candidate arrays remain artifacts.
            selected = document.get("summary", document)
            run.log(scalar_metrics(selected, Path(filename).stem))
        print(json.dumps({"run_id": run.id, "url": run.url}), flush=True)


if __name__ == "__main__":
    main()
