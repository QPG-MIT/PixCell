"""Qualify identity, real text generation and image understanding; no dependencies."""

import argparse
import base64
import datetime
import json
import struct
import time
import urllib.request
import zlib
from pathlib import Path

# The cluster's system Python predates datetime.UTC; this client uses only stdlib.
UTC = datetime.timezone.utc  # noqa: UP017


def blue_square_png():
    """A deterministic visual transport probe, never a PixCell benchmark fixture."""
    size = 224
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            row.extend((0, 0, 255) if 32 <= x < 192 and 32 <= y < 192 else (255, 255, 255))
        rows.append(bytes(row))

    def chunk(name, payload):
        return (
            struct.pack("!I", len(payload))
            + name
            + payload
            + struct.pack("!I", zlib.crc32(name + payload))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!2I5B", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(rows)))
        + chunk(b"IEND", b"")
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    run = args.run_dir
    metadata = json.loads((run / "metadata.json").read_text())
    key = (run / "api-key").read_text().strip()
    base = f"http://127.0.0.1:{metadata['port']}"

    def request(path, body=None):
        raw = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(
            base + path,
            data=raw,
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        )
        started = time.monotonic()
        with urllib.request.urlopen(req, timeout=180) as response:
            result = json.load(response)
        return {"seconds": time.monotonic() - started, "response": result}

    evidence = {
        "metadata": metadata,
        "started_at": datetime.datetime.now(UTC).isoformat(),
        "scope": "serving only; no training or PixCell quality claim",
        "checks": {},
    }
    try:
        models = request("/v1/models")
        evidence["models"] = models
        evidence["checks"]["model_identity"] = metadata["served_model"] in [
            item["id"] for item in models["response"]["data"]
        ]
        common = {
            "model": metadata["served_model"],
            "temperature": 0,
            "max_tokens": 1024,
            "chat_template_kwargs": {"reasoning_effort": "low"},
        }
        text = request(
            "/v1/chat/completions",
            dict(
                common,
                messages=[
                    {
                        "role": "user",
                        "content": "Reply with exactly CONTRACT_TEXT_OK and nothing else.",
                    }
                ],
            ),
        )
        evidence["text"] = text
        text_response = text["response"]
        evidence["checks"]["text_generation"] = (
            text_response.get("model") == metadata["served_model"]
            and text_response["choices"][0]["message"].get("content", "").strip()
            == "CONTRACT_TEXT_OK"
        )
        png = blue_square_png()
        (run / "vision_probe.png").write_bytes(png)
        vision = request(
            "/v1/chat/completions",
            dict(
                common,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "What color is the large filled square in this image? Reply with exactly one lowercase color word.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "data:image/png;base64," + base64.b64encode(png).decode()
                                },
                            },
                        ],
                    }
                ],
            ),
        )
        evidence["vision"] = vision
        vision_response = vision["response"]
        evidence["checks"]["image_understanding"] = (
            vision_response.get("model") == metadata["served_model"]
            and vision_response["choices"][0]["message"]
            .get("content", "")
            .strip()
            .lower()
            .rstrip(".")
            == "blue"
        )
        evidence["passed"] = all(evidence["checks"].values())
    except Exception as exc:
        evidence["passed"] = False
        evidence["error"] = type(exc).__name__ + ": " + str(exc)
        raise
    finally:
        evidence["finished_at"] = datetime.datetime.now(UTC).isoformat()
        (run / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(
        json.dumps(
            {"passed": evidence["passed"], "checks": evidence["checks"], "run_dir": str(run)}
        )
    )
    if not evidence["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
