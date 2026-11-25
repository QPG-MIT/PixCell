# GLM-5.3-Flash: serving and visual-training feasibility

Research snapshot: **2026-10-04 America/Chicago / October 5 UTC**. Upstream
observations below are distinguished from the actual Engaging qualifications.

**Dedicated native-FP8 GLM-5.3-Flash inference has now passed text and image
checks on two Engaging B200s.** Job `24879182` also generated two real PixCell
L0 candidate programs. Generation alone does not certify their geometry or
establish learning. The unresolved GLM task is visual training: an inference
endpoint does not implement backward passes, optimizer updates, or checkpoint
synchronization. A separate one-B200 Qwen optimizer qualification **passed** as
job `24879834`: one actual image-conditioned adapter update, then exact
save/reload checks. [Actual deployment and evidence locations](infra/README.md).

## Exact model and memory

The requested model exists; it is not a typo for GLM-4.7-Flash.
`zai-org/GLM-5.3-Flash` is an MIT-licensed, natively multimodal MoE with about
320B total parameters and 18B active per token. It accepts image/video/text and
produces text. Its first-party release is FP8; the BF16 release is a separate
repository. Active parameters reduce per-token work, not the number of weights
that need storage. [Z.ai model card](https://huggingface.co/zai-org/GLM-5.3-Flash),
[Z.ai API documentation](https://docs.z.ai/guides/vlm/glm-5.3-flash).

The following byte counts were computed by summing `siblings[].size` for
`.safetensors` files from the public Hugging Face API (`?blobs=true`). They are
checkpoint-file sizes, not measured peak GPU allocations. Cache, activations,
runtime buffers, adapters, and optimizer state add memory.

These public revisions are **not** the revision served in the qualified Engaging
job. That job deliberately reused the owner's checksum-verified cached release
`03eb5366286afd40d2221b1d9c63a6dd1ba4832e` and existing SIF image, SHA-256
`87f6ab3d16ae98673bc4eba2e496a37e06cd67cdcab661e33171482e940950ae`.
Its checkpoint index records 328,326,771,576 bytes. Keep these identities
distinct; new upstream revisions require their own qualification.

| Checkpoint | Revision inspected | Weight bytes | GiB |
|---|---|---:|---:|
| [Z.ai FP8](https://huggingface.co/zai-org/GLM-5.3-Flash/tree/eb9eb208eb0d988989d07a6a12d0fdeb5f52574a) | `eb9eb208eb0d988989d07a6a12d0fdeb5f52574a` | 328,337,455,672 | 305.788 |
| [Z.ai BF16](https://huggingface.co/zai-org/GLM-5.3-Flash-BF16/tree/a5b45eb41df6402735dedc900be14a42e8d5e538) | `a5b45eb41df6402735dedc900be14a42e8d5e538` | 642,652,070,880 | 598.516 |
| [NVIDIA NVFP4](https://huggingface.co/nvidia/GLM-5.3-Flash-NVFP4/tree/da920bb0b9f4a06727223a349e55468e38352348) | `da920bb0b9f4a06727223a349e55468e38352348` | 204,439,103,396 | 190.399 |
| [Red Hat NVFP4](https://huggingface.co/RedHatAI/GLM-5.3-Flash-NVFP4/tree/18d55bfd5a2194887738da73753975c9d3842f46) | `18d55bfd5a2194887738da73753975c9d3842f46` | 197,843,812,476 | 184.256 |

NVIDIA's HGX documentation lists B200 SXM at 180 GB per GPU; the actual scheduler
allocation must be checked with `nvidia-smi`. Even the two inspected NVFP4
checkpoints exceed that budget before runtime overhead.
[NVIDIA HGX specifications](https://docs.nvidia.com/enterprise-reference-architectures/hgx-ai-factory-h100-h200-b200/latest/components.html).

| Resources | Current evidence and intended use |
|---|---|
| 1 B200 | Qwen3-VL-30B-A3B image-conditioned attention LoRA **qualified locally** at a 94-token synthetic-example length, with 58.0 GiB peak allocated memory. GLM heavily quantized inference is a separate option. |
| 2 B200 | Native FP8 GLM serving **qualified locally** at TP2, 8K context, two concurrent sequences, one image per prompt. Additional context/concurrency needs measurement. |
| 4 B200 | Upstream TP4 recipe and extra serving headroom; not required for our qualified bounded workload and not a training-memory guarantee. |
| 8+ B200 | Investigate training only after a backward-pass and multimodal-support audit. Number alone is insufficient. |

Unsloth documents single-B200 **inference** with a 1-bit GGUF and offers 1–3-bit
variants. Its published quantization analysis shows material divergence from
BF16 at aggressive compression. That is useful for an exploratory server, but
does not establish QLoRA/backward support or preserve a clean training-signal
comparison. [Unsloth's GLM-5.3-Flash guide](https://unsloth.ai/docs/models/glm-5.3-flash).

## Qualified inference path

Use [serve_glm_smoke.sh](infra/serve_glm_smoke.sh), which reuses the pinned cached
release at TP2 with FP8 KV, eager execution, 8,192-token context, and a 0.95
memory fraction. It passed model identity, text generation, and PNG image
understanding on `node5501-c1`. It is a **30-minute bounded Slurm job**, not a
persistent service or a training job. The existing production deployments and
routes were left unchanged. The actual [infra runbook](infra/README.md) is the
launch procedure for reproducing this qualification.

The upstream vLLM recipe specifies native FP8 weights, roughly 306 GiB weight
memory, FlashInfer >=0.6.17, and a TP4 launch. It identifies vLLM >=0.29.0 while
still directing readers to a dedicated/nightly image during integration.
SGLang documents support in >=0.5.20, multimodal serving, and separate KV/KDA
state pools. These are context for future runtime upgrades; the qualified
Engaging script already pins its cached image instead of installing a floating
upstream build.
[vLLM recipe](https://recipes.vllm.ai/zai-org/GLM-5.3-Flash),
[SGLang recipe](https://docs.sglang.io/cookbook/autoregressive/GLM/GLM-5.3-Flash).

Record model revision, image digest, exact command, driver/CUDA versions,
topology, `nvidia-smi` memory, processor/chat-template revisions, and request
payloads. Prove image handling with same-text/different-image examples, then
run actual held-out PixCell fixtures. A `/v1/models` response alone proves
neither vision nor task correctness. Bound response tokens and record
`reasoning_effort`; reasoning is always enabled for this model, with low/high/max
effort settings. [Z.ai parameter contract](https://docs.z.ai/guides/vlm/glm-5.3-flash).

## Training support is narrower than inference support

**The strongest merged evidence found is language-only training.**
[SkyRL PR #2179](https://github.com/NovaSky-AI/SkyRL/pull/2179), merged September
28 (`415a954084b41fd801b58a9b24507c4e734bbae6`), adds Megatron full fine-tuning
and LoRA synchronization to vLLM. It vendors architecture and LoRA patches,
tests KDA/mHC kernels and adapter synchronization, and reports full-model runs
on 64 B200s. It explicitly uses `language_model_only=True`. Those measurements
do not validate learning from image-conditioned examples.

The upstream [single-node LoRA smoke recipe](https://github.com/NovaSky-AI/SkyRL/blob/5f9a1be2eaf3f267cfc158a11bcc91c7fd55faa1/examples/train/glm5_3_flash/run_gsm8k_glm5p3_flash_lora_1node.sh)
targets **8 B300s**, uses the BF16 checkpoint, and sleeps the colocated inference
engine during training. Its comments warn that the SkyRL bridge can mishandle
FP8 scale sidecars when importing the default checkpoint. It requires explicit
LoRA targets; generic `all-linear` is insufficient for the architecture. Thus
the release's small active count and FP8 inference format do not imply a cheap
training configuration.

The [two-node LoRA recipe](https://github.com/NovaSky-AI/SkyRL/blob/5f9a1be2eaf3f267cfc158a11bcc91c7fd55faa1/examples/train/glm5_3_flash/run_dapo_glm5p3_flash_lora_sync_2node.sh)
uses 16 B300s by default and explicitly directs B200 users to EP=16 because
EP=8 runs out of memory during backward. Its rollout-routing replay path is
incompatible with its vision-language generator. Treat these as current
integration constraints, not a proof that visual RL is impossible.

[Megatron-Bridge PR #6044](https://github.com/NVIDIA-NeMo/Megatron-Bridge/pull/6044)
was **open** when inspected. It adds a replicated vision tower, image/video
feature injection, freeze options, and KDA PEFT conversion. Its own description
says the VLM wrapper needs Transformers 5.17 while the repository pin is
<=5.15, and a functional HF/Megatron round trip is still a follow-up.
[vLLM LoRA PR #56327](https://github.com/vllm-project/vllm/pull/56327) was also
open; it repairs GLM's adapter-to-fused-projection mapping. Mere inheritance of
`SupportsLoRA` was not sufficient. A merged inference loader should never be
treated as evidence of a correct training/rollout loop.

**Recommended GLM visual-training acceptance sequence** (proposed engineering
checks, not completed work):

1. Pin a trainer/backend combination and run a short image-conditioned forward
   and backward pass, first on an architectural slice if necessary. Verify
   finite loss, expected trainable parameter count, finite nonzero adapter
   gradients, and frozen-base invariance. A slice is not a capacity benchmark
   for the full model.
2. Change the input image while holding the prompt fixed. Verify the processor
   produces image tensors and that logits/loss respond. Explicitly distinguish
   a frozen vision encoder with a trainable language adapter from training the
   encoder itself; both require image-conditioned forward computation.
3. Overfit a tiny synthetic set with contradictory visual labels. Require loss
   reduction and learned image dependence, then save/reload the adapter and
   confirm identical predictions. This validates plumbing, not generalization.
4. Publish a deliberately changed adapter to the rollout engine. Compare
   trainer and sampler log probabilities for identical image/text inputs,
   tokenization, precision, and templates. Check both short and long prompts.
   A stale sampler makes an apparently running RL job scientifically invalid.
5. Only after that, run the matched-budget signal ablation with held-out
   component families and artifact-derived conductor metrics. Track failures,
   GPU-hours, tokens, memory, and learning curves in W&B.

## Practical one-GPU training lane

Engaging already contains a self-hosted Qwen training implementation and saved
training artifacts from July 8. Read-only inspection found
`/orcd/home/002/aadarwal/PixCell-running/rl/local/grpo.py` and `renderer.py`, plus
the run
`/orcd/scratch/orcd/010/aadarwal/pixcell/runs/smoke-qwen/pixcellg-Qwen3-VL-30B-A3B-Instruct-8g-2b-lr1e-05-20260708-1428`.
Its config records source revision `957dddf2`, and its directory contains
adapters, optimizer/checkpoint records, and train/eval logs. This is evidence of
previous local training work; the historical metrics have not been independently
regated and are not new experimental results.

The existing implementation passes processor image tensors through the learner,
trains language LoRA while freezing the vision tower, and uses a separate vLLM
sampler. It includes a strict sampler/learner token-ID identity check. Reusing
its cached weights and environment is preferable to installing an unrelated
stack; importing its entire old GRPO/reward implementation into the new branch
would also import historical choices that require review.

The immediate smoke therefore targets the already cached
`Qwen/Qwen3-VL-30B-A3B-Instruct`, revision
`9c4b90e1e4ba969fd3b5378b57d966d725f1b86c`, with the existing Python 3.12,
Torch 2.11/CUDA 13.0, Transformers 5.13, PEFT 0.19.1, and Accelerate 1.14
environment. `training_smoke.py` uses a rank-4 attention adapter, two 256px
synthetic images, and one optimizer step. Each prompt expands to 90 tokens and
each full example to 94; exact prefix matching and image/grid tensors are
checked before training.

Job `24879834` **passed on an actual B200**. It trained 1,671,168 adapter
parameters across 96 q/v projection modules, measured a nonzero gradient norm
of 0.021525, and changed adapter weights by a maximum of approximately 1e-4.
Changing the image under the identical tokenized prompt changed next-token
logits (maximum absolute difference 18.125). After destroying the in-memory
adapter and loading it from disk, all saved adapter tensors matched exactly
and prediction-logit difference was zero. Frozen parameter version counters
were unchanged. Peak allocated GPU memory was 62,281,966,080 bytes (58.0 GiB),
peak reserved memory 63,025,709,056 bytes (58.70 GiB), and elapsed model-load plus
qualification time was 114.20 seconds. This proves the bounded own-compute
image-conditioned optimizer/save/reload path, not GLM training, sustained
learning, long-context capacity, or sampler synchronization. Job config,
metrics, and result are copied under `infra/runtime/train-24879834/` (runtime
artifacts are ignored by Git); remote originals are at
`/orcd/scratch/orcd/010/aadarwal/contract-algos/training/24879834/result/`.

Use a compact visual model to validate the experiment while the requested GLM
server is brought up separately. This is an explicit second model, not a silent
substitution. GLM-4.6V-Flash is a 9B visual model with approximately 19.17 GiB of
BF16 checkpoint files; its API revision inspected was
`411bb4d77144a3f03accbf4b780f5acb8b7cde4e`.
[GLM-4.6V-Flash](https://huggingface.co/zai-org/GLM-4.6V-Flash).

For a lower-risk trainer integration, consider Qwen2.5-VL-3B/7B or a Qwen3.5-9B
pilot. TRL documents image-conditioned SFT and image-token truncation hazards;
NeMo AutoModel has a Qwen3.5-9B image/text recipe. A one-B200 LoRA fit is an
engineering expectation at controlled resolution/context, not a measured result
here. Keep the vision encoder frozen initially, then test encoder/projector
adaptation as a separate ablation if needed.
[TRL VLM training](https://huggingface.co/docs/trl/v0.28.0/en/sft_trainer),
[Qwen3.5-9B recipe](https://docs.nvidia.com/nemo/automodel/nightly/model-coverage/vision-language-models/qwen/Qwen3.5-9B).

Do not select GLM-4.7-Flash as a visual substitute: it is a 30B-A3B text model.
[GLM-4.7-Flash model card](https://huggingface.co/zai-org/GLM-4.7-Flash).

## What changes when moving off Tinker

Tinker exposes `forward_backward`, `optim_step`, `sample`, and checkpoint
operations while managing distributed execution. It supports LoRA rather than
full fine-tuning and includes visual models. On owned compute, PyTorch plus
PEFT/TRL or a distributed training framework can perform the same classes of
updates, but we own memory placement, batching, image preprocessing, failures,
checkpointing, and sampler synchronization.
[Tinker overview](https://tinker-docs.thinkingmachines.ai/).

The public Tinker model catalog inspected contains GLM-5.3, but not
GLM-5.3-Flash. These are different models. Query authenticated server
capabilities before treating the catalog as final availability.
[Machine-readable Tinker catalog](https://tinker-docs.thinkingmachines.ai/tinker/models.json).

For the signal study, hold data splits, initial weights, sampling budget,
precision, reward scaling, and token masking fixed. Start with a baseline and
supervised successful trajectories, then compare scalar artifact rewards with
structured per-step feedback. A reward affects parameter learning only when a
trainer turns it into a loss and updates weights. A dedicated inference server
alone supports rollout collection and evaluation, not that update. W&B records
the experiment; it does not provide the training backend.

Remaining GLM evidence needed: an image-conditioned backward pass, a validated
adapter save/reload and trainer/sampler round trip, and full-model peak training
memory at our image and sequence budget. Engaging inventory, existing quota
access, container compatibility, and bounded TP2 serving have already been
checked and are recorded in the [infra runbook](infra/README.md).
