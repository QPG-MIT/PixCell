# Dedicated Engaging inference qualification

`serve_glm_smoke.sh` serves the immutable, cached GLM-5.3-Flash checkpoint in a
bounded Slurm job. It verifies the existing asset checksum record, binds the HF
cache read-only, uses an isolated runtime directory, generates a fresh private
API key, and listens on compute-node loopback port 18153. It does not submit
successors or publish a public route. Runtime files and credentials are ignored
by Git.

The existing GLM deployment proves that native FP8 inference fits on **two B200s**.
This script qualifies inference only. It neither changes weights nor establishes
that GLM image training is supported.

The measured initial profile used an 8192-token context. Actual PixCell prompts
used 4938–4987 tokens, and one grouped rollout hit the remaining 3205-token
generation limit. The replacement development allocation uses
`CONTRACT_MAX_MODEL_LEN=16384` and passed actual text and image serving checks.
It consumed 150.95 GiB for weights/non-Torch memory, 2.65 GiB peak activation,
and 15.83 GiB KV cache per GPU. Benchmark throughput at this context size is
not measured. CUDA graphs, MTP and larger concurrency likewise require a
separately recorded throughput/quality qualification.

**Current development instance:** job `24881211` (`pixcell-contract-glm-dev`),
two B200s on `node5501-c1`, private `127.0.0.1:18153`, served alias
`contract-glm53-flash`. At **2026-10-05 03:15:14 UTC**, exact model identity,
text generation (`CONTRACT_TEXT_OK`, 1.00s) and image understanding (`blue`,
0.41s) passed. Its two-hour allocation ends **2026-10-05 05:10:57 UTC**, or
**October 5, 00:10:57 Chicago time**. It has no automatic successor.
Evidence is in `runtime/24881211/`; the fresh authentication key stays only
in the corresponding private remote runtime directory.

## Submit

SSH alias `engaging` must already authenticate. Copy these two scripts into
`/orcd/scratch/orcd/010/aadarwal/contract-algos/infra/`, then run:

```bash
ssh engaging 'sbatch --parsable --job-name=pixcell-contract-glm \
  --partition=mit_testing --nodes=1 --gres=gpu:b200:2 \
  --cpus-per-task=32 --mem=384G --time=00:30:00 \
  --chdir=/orcd/scratch/orcd/010/aadarwal/contract-algos \
  --output=/orcd/scratch/orcd/010/aadarwal/contract-algos/runtime/slurm-%j.out \
  /orcd/scratch/orcd/010/aadarwal/contract-algos/infra/serve_glm_smoke.sh \
  /orcd/scratch/orcd/010/aadarwal/contract-algos'
```

The initial submission on 2026-10-05 UTC was job `24879182`. Its requested
walltime is 30 minutes; it must not be described as a persistent service.
At 02:48:23 UTC, this job passed exact model identity, text generation
(`CONTRACT_TEXT_OK`, 1.97s) and PNG image understanding (`blue`, 0.63s).
Fresh isolated kernel caches made startup approximately eight minutes.
These are serving qualification results, not a training result.
An owner request to extend this exact job to two hours was rejected by Slurm
(`Access/permission denied`); no escalation was attempted. It ended at its
original deadline, **2026-10-05 03:10:14 UTC**. The replacement above was
submitted separately, after that allocation ended, with a two-hour limit.

## Read evidence and connect

`runtime/JOB_ID/metadata.json` records node, port, revision and asset identity.
`evidence.json` contains actual text and image responses and explicit checks.
`gpus.csv`, `slurm.txt`, and `server.log` record resources and startup evidence.
The probe requires the exact served alias, a fixed text marker, and the correct
color from a generated PNG; these checks establish working serving, not model
quality or learning.

Read the assigned node with `ssh engaging 'squeue -j JOB_ID -h -o %N'`. To
reach the loopback listener, use a tunnel terminating on that compute node,
for example:

```bash
ssh -N -J engaging -L 127.0.0.1:18153:127.0.0.1:18153 aadarwal@ASSIGNED_NODE
```

This requires SSH access to one's assigned compute node. Alternatively, execute
the client as a Slurm job step in the same allocation. A tunnel only to the
Engaging login node cannot reach the compute node's loopback listener. Keep the
per-job `api-key` out of command arguments, logs, and source; read it inside a
client process and set its Authorization header in memory. No public DNS or
production model route is needed.

To stop early, inspect the exact job with `scontrol show job JOB_ID`, verify
its name and owner, then `scancel JOB_ID`. Do not cancel by a broad name pattern.

## Live inventory observed 2026-10-05 02:37 UTC

- Engaging user `aadarwal` belongs to `orcd_rg_par_ou_orcd_testing` and has working
  SSH. `mit_testing` allows that group, has a 7-day job maximum, non-preemptive
  policy, 12 eight-B200 nodes plus one eight-B300 node. `mit_user_testing` overlaps
  six of those B200 nodes. They are not additive pools.
- Six B200 nodes were idle and three were reserved. Idle/reserved does not
  guarantee immediate eligibility. Production GLM replicas and Inkling already
  occupy assigned GPUs on nodes `node5501-c1` and `node5502-c1`; leave those
  allocations and their services unchanged.
- Existing cached inference image:
  `/orcd/scratch/orcd/010/aadarwal/llm/images/vllm-glm53-flash.sif`.
  Model revision: `03eb5366286afd40d2221b1d9c63a6dd1ba4832e`.
  The checkpoint index records 328,326,771,576 bytes. Existing production logs
  report 154.18 GiB model allocation per GPU at TP2, with startup about 3m36s.
- A separate complete Qwen3-VL-30B-A3B-Instruct BF16 cache exists under
  `/orcd/scratch/orcd/010/aadarwal/pixcell/hf/hub/`, revision
  `9c4b90e1e4ba969fd3b5378b57d966d725f1b86c`, 13/13 shards, 62.14 GB.
  The existing `pixcell/envs/rl` environment includes PyTorch 2.11.0,
  Transformers 5.13.0, PEFT 0.19.1 and Accelerate 1.14.0. This is a promising
  smaller image-training candidate; installed packages alone do not prove a
  successful optimizer step.
- AICR SSH alias `aicr` also works. Its B200 batch pool was occupied at audit
  time; its batch GPU QOS limit is 32 GPUs per user, development limit two.
  Engaging is the practical first choice for this experiment.
- `compute.nonlocally.org` responds but redirects unauthenticated visitors to
  GitHub sign-in. Scheduler observations above came directly from SSH/Slurm.

## Bounded Qwen optimizer qualification

`train_qwen_smoke.sh` runs `../training_smoke.py` using the existing cached
Qwen3-VL-30B-A3B-Instruct model and existing Python environment. Its output and
all writable caches are isolated under `contract-algos/training/JOB_ID/`.
The first submission was job `24879834`, requesting one B200, 16 CPU cores,
128 GiB host RAM, and 15 minutes on `mit_testing`. It performs one optimizer
step on two synthetic image examples, checks actual image dependence, nonzero
adapter gradients and parameter updates, then saves and reloads the adapter.
The frozen vision encoder and MoE experts are unchanged; this qualifies
image-conditioned attention LoRA, not GLM training or benchmark learning.

Copy `../training_smoke.py` and `train_qwen_smoke.sh` into the isolated remote
`contract-algos/infra/` directory, then submit explicitly:

```bash
ssh engaging 'sbatch --parsable --job-name=pixcell-contract-train \
  --partition=mit_testing --nodes=1 --gres=gpu:b200:1 \
  --cpus-per-task=16 --mem=128G --time=00:15:00 \
  --chdir=/orcd/scratch/orcd/010/aadarwal/contract-algos \
  --output=/orcd/scratch/orcd/010/aadarwal/contract-algos/runtime/train-%j.out \
  /orcd/scratch/orcd/010/aadarwal/contract-algos/infra/train_qwen_smoke.sh \
  /orcd/scratch/orcd/010/aadarwal/contract-algos'
```

Inspect `training/JOB_ID/result/result.json` for an explicit passing result.
`config.json` pins the checkpoint, script hash and package versions;
`metrics.jsonl` records each phase. The Slurm log is `runtime/train-JOB_ID.out`.
Copy only these selected result files for telemetry; the full model remains in
its original cache. No checkpoint from this smoke is promoted automatically.

Job `24879834` completed successfully (`COMPLETED`, `0:0`) at
2026-10-05 02:53:50 UTC after 2m39s total allocation time. Its measured checks:

- 1,671,168 trainable parameters across 96 attention q/v projections.
- Nonzero gradient norm 0.021525 and adapter maximum absolute update 0.000100.
- Changing the image changed next-token logits (maximum absolute delta 18.125).
- Saved/reloaded adapter predictions were identical (maximum logit delta 0).
- Frozen base parameter version counters stayed unchanged.
- Peak allocated CUDA memory 62,281,966,080 bytes (58.0 GiB).

This establishes a real local optimizer step and checkpoint round trip on the
image-conditioned smaller model. Two easy synthetic examples do not establish
which training signal works best, generalization, or trainability of GLM itself.
