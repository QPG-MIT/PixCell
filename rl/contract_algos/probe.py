"""Collect immutable image-to-code rollouts from a dedicated OpenAI endpoint.

This is an inference probe, not a trainer. Only ModelObservation reaches the
model; labels and verifier references remain local to the later audit.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlparse

import httpx

from rl.common.prompt import CONTRACT_VERSION, openai_user_message, prompt_asset_hashes


def request_body(task, *, model: str, max_tokens: int, temperature: float) -> dict:
    image_url = "data:image/png;base64," + base64.b64encode(
        task.observation.image_bytes
    ).decode("ascii")
    return {
        "model": model,
        "messages": [openai_user_message(task.observation, image_url=image_url)],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }


def validate_response(response: dict, expected_model: str) -> tuple[str, str]:
    if response.get("model") != expected_model:
        raise ValueError(f"endpoint returned unexpected model {response.get('model')!r}")
    choices = response.get("choices", [])
    if len(choices) != 1:
        raise ValueError("endpoint must return exactly one choice")
    choice = choices[0]
    content = choice.get("message", {}).get("content")
    if choice.get("finish_reason") == "length" and content in (None, ""):
        # Exhausting the budget in reasoning is a sampled failure, not a reason
        # to silently remove this attempt from the experiment's denominator.
        return "", "length"
    if not isinstance(content, str) or not content.strip():
        raise ValueError("endpoint returned no assistant completion")
    return content, str(choice.get("finish_reason", "unknown"))


def main() -> None:
    from rl.contract_algos.splits import load_release, verify_manifest

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, default=Path("dataset"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--deployment-metadata", type=Path, required=True,
                        help="Allocated server metadata.json with model revision and image digest")
    parser.add_argument("--base-url", required=True, help="Dedicated server /v1 URL")
    parser.add_argument("--model", default="contract-glm53-flash")
    parser.add_argument("--api-key-env", default="CONTRACT_ALGOS_API_KEY")
    parser.add_argument("--partition", choices=["train", "validation", "test"], default="train")
    parser.add_argument("--level", default="L0")
    parser.add_argument("--tasks", type=int, default=2)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()
    if min(args.tasks, args.attempts, args.max_tokens) <= 0:
        parser.error("tasks, attempts, and max-tokens must be positive")
    parsed = urlparse(args.base_url)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        parser.error("use an HTTP(S) endpoint without credentials in the URL")
    if parsed.query or parsed.fragment:
        parser.error("endpoint URL must not contain query parameters or fragments")
    manifest = json.loads(args.manifest.read_text())
    verify_manifest(manifest, args.dataset_root)
    deployment = json.loads(args.deployment_metadata.read_text())
    if any(not deployment.get(key) for key in ("model", "revision", "served_model", "image_sha256")):
        parser.error("deployment metadata must identify model, revision, served_model and image_sha256")
    if deployment["served_model"] != args.model:
        parser.error("requested model differs from the recorded deployment")
    ids = sorted(
        row["task_id"] for row in manifest["rows"]
        if row["split"] == args.partition and row["level"] == args.level
    )[:args.tasks]
    if len(ids) != args.tasks:
        parser.error("not enough tasks in the requested partition and level")
    tasks = {t.sampler.opaque_id: t for t in load_release(args.dataset_root)}
    headers = {}
    if key := os.environ.get(args.api_key_env):
        headers["Authorization"] = f"Bearer {key}"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents an accidental retry from overwriting samples.
    with args.out.open("x") as output, httpx.Client(
        base_url=args.base_url.rstrip("/") + "/",
        headers=headers, timeout=args.timeout, trust_env=False,
    ) as client:
        models_response = client.get("models")
        models_response.raise_for_status()
        models = models_response.json()
        if args.model not in {m["id"] for m in models.get("data", [])}:
            raise ValueError("requested model is not advertised by the endpoint")
        for task_id in ids:
            for attempt in range(args.attempts):
                body = request_body(
                    tasks[task_id], model=args.model, max_tokens=args.max_tokens,
                    temperature=args.temperature,
                )
                with args.out.with_name(
                    f"{args.out.stem}-{task_id}-{attempt:03d}.request.json"
                ).open("x") as request_output:
                    json.dump(body, request_output, allow_nan=False)
                started = time.monotonic()
                response = client.post("chat/completions", json=body)
                # Persist successful HTTP payload before parsing/scoring it.
                response.raise_for_status()
                raw = response.json()
                raw_path = args.out.with_name(
                    f"{args.out.stem}-{task_id}-{attempt:03d}.response.json"
                )
                with raw_path.open("x") as raw_output:
                    json.dump(raw, raw_output, allow_nan=False)
                completion, finish_reason = validate_response(raw, args.model)
                record = {
                    "task_id": task_id,
                    "candidate_id": f"sample-{attempt:03d}",
                    "completion": completion,
                    "model": args.model,
                    "deployment": deployment,
                    "manifest_sha256": manifest["manifest_sha256"],
                    "prompt_contract": CONTRACT_VERSION,
                    "prompt_assets": prompt_asset_hashes(),
                    "request_sha256": hashlib.sha256(
                        json.dumps(body, sort_keys=True).encode()
                    ).hexdigest(),
                    "temperature": args.temperature,
                    "max_tokens": args.max_tokens,
                    "finish_reason": finish_reason,
                    "truncated": finish_reason == "length",
                    "usage": raw.get("usage"),
                    "response": raw,
                    "latency_seconds": time.monotonic() - started,
                    "training_performed": False,
                }
                output.write(json.dumps(record, allow_nan=False) + "\n")
                output.flush()
                print(json.dumps({k: record[k] for k in (
                    "task_id", "candidate_id", "finish_reason", "usage", "latency_seconds"
                )}), flush=True)


if __name__ == "__main__":
    main()
