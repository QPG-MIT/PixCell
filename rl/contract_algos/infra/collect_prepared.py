#!/usr/bin/env python3
"""Run explicit prepared image requests inside the private Slurm allocation.

Input records contain task_id, candidate_id, body and manifest_sha256. Bodies
are prepared with rl.contract_algos.probe.request_body; no labels are uploaded.
The credential stays on the compute node and is never a command-line argument.
"""

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import time
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()
    metadata = json.loads((args.run_dir / "metadata.json").read_text())
    key = (args.run_dir / "api-key").read_text().strip()
    items = json.loads(args.requests.read_text())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as output:
        for index, item in enumerate(items):
            body = item["body"]
            if body["model"] != metadata["served_model"]:
                raise ValueError("prepared request model differs from allocated model")
            raw = json.dumps(body).encode()
            with args.out.with_name(f"{args.out.stem}-{index}.request.json").open("x") as request_file:
                json.dump(item, request_file, allow_nan=False)
            req = urllib.request.Request(
                "http://127.0.0.1:%s/v1/chat/completions" % metadata["port"], data=raw,
                headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            )
            started = time.monotonic()
            with urllib.request.urlopen(req, timeout=args.timeout) as response:
                result = json.load(response)
            with args.out.with_name(f"{args.out.stem}-{index}.response.json").open("x") as response_file:
                json.dump(result, response_file)
            if result.get("model") != metadata["served_model"]:
                raise ValueError("unexpected returned model identity")
            choice = result["choices"][0]
            completion = choice["message"].get("content")
            if choice.get("finish_reason") == "length" and completion in (None, ""):
                completion = ""
            if not isinstance(completion, str) or (
                not completion.strip() and choice.get("finish_reason") != "length"
            ):
                raise ValueError("no completion; raw response retained for diagnosis")
            record = {
                "task_id": item["task_id"], "candidate_id": item["candidate_id"],
                "manifest_sha256": item["manifest_sha256"], "completion": completion,
                "model": metadata["model"], "served_model": metadata["served_model"],
                "revision": metadata["revision"], "image_sha256": metadata["image_sha256"],
                "job_id": metadata["job_id"], "request_sha256": hashlib.sha256(raw).hexdigest(),
                "max_tokens": body["max_tokens"], "temperature": body["temperature"],
                "chat_template_kwargs": body.get("chat_template_kwargs"),
                "usage": result.get("usage"), "finish_reason": choice.get("finish_reason"),
                "truncated": choice.get("finish_reason") == "length", "response": result,
                "latency_seconds": time.monotonic() - started,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "training_performed": False,
            }
            output.write(json.dumps(record, allow_nan=False) + "\n")
            output.flush()
            print(json.dumps({k: record[k] for k in (
                "task_id", "finish_reason", "usage", "latency_seconds"
            )}), flush=True)


if __name__ == "__main__":
    main()
