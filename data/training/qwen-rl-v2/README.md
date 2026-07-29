# Qwen RL v2 — evidence for the released model

The validated record behind the released PixCell model
([`qpaig-mit/pixcell`](https://huggingface.co/qpaig-mit/pixcell)): a LoRA
adapter for `Qwen/Qwen3.6-35B-A3B` trained with GRPO alone (no SFT) on the
released curriculum L0→L4 at the non-thinking 4096-token operating point —
Run B of the campaign recipe in [`rl/`](../../../rl/README.md). Checkpoint of
record: `tinker://d8269c70-0dd9-5776-9cae-53e8b24e647a:train:0/sampler_weights/final`.

Per the repository rule, every number here was recomputed from artifacts by
the deterministic evaluator; nothing model-reported enters the record.

## Files

| Path | Protocol | Headline |
|---|---|---|
| `bench/base-nothink.json` | F1–F8, 8 attempts @ T=1.0, best-of-8 raw IoU | base model: 0/64 attempts executable |
| `bench/b-final.json` | same | released model: 39/64 executable, mean IoU 0.228, best-of-8 0.467 |
| `bench/a-post-l1.json`, `bench/d-post-l0.json` | same | mid-campaign controls (L0-SFT arm after L1; thinking arm after L0) |
| `agentloop/b-final.json` | attempt–measure–revise loop: 8 attempts, then 3 rounds × 4 revisions of the champion under number-free feedback | **mean champion IoU 0.491**; includes every champion program and per-round trajectory |

The agent loop is the deployment protocol — the released model is the
searcher inside that loop, and 0.491 is its number. The single-pass benchmark
is the ablation that shows what a bare forward pass gives up.

## Recompute

```bash
uv run python -m rl.track_a.benchmark_eval --model-path <checkpoint> --out bench.json
uv run python -m rl.track_a.agent_loop     --model-path <checkpoint> --out agentloop.json
uv run python -m rl.track_a.make_gallery   --champions agentloop.json --out-dir gallery/
```

The render gallery (per device: target | champion render | difference map)
is not stored here: `make_gallery` re-executes each stored champion program
from source and re-renders it against the frozen `data/benchmark` fixtures,
so it regenerates from this record alone, no checkpoint required. The
composite ships on the [model card](https://huggingface.co/qpaig-mit/pixcell).
