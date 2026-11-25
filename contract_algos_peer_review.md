# Peer review: visual-signal comparison plan and the self-hosted GLM path

Reviewer: pixcell-8a (Claude session 06b7da1b), 2026-10-04 evening.
Revised the same night after root's corrections: the SkyRL EP=16 finding,
my overstated smoke-throughput claim, and the vision-trainer phrasing; and
after root's `extract_polygons` fix (Sec. 2.7).
Scope: read-only. PixCell `main` @ 533752c1 (`rl/`, `research-contracts/`,
`data/training`, `arxiv/main.tex` Sec. V), Engaging over ssh (`sinfo`,
`scontrol`, `squeue`, `sacct`, job scripts, logs, quotas), and today's
fetches of the Tinker models page, the vLLM GLM-5.3-Flash recipe, vLLM PR
#56327, SkyRL PR #2226, the HF model card. No jobs submitted, nothing
changed on the cluster or in production services.

## 0. Bottom line

1. Run the signal comparison where it is cheap and already instrumented:
   Tinker + `Qwen/Qwen3.6-35B-A3B`, the paper's lineage. My estimate is
   about $100 per 150-step run (Sec. 4), so 4 arms x 3 seeds is about $1.3k.
   GLM-5.3-Flash is not on Tinker (only the text-only `GLM-5.3 (256K)` is),
   and none of the trainer paths I inspected (SkyRL/Megatron, the vLLM LoRA
   PR, slime, ms-swift) has a verified vision path for it. Building one is a
   multi-week infrastructure project with unverified numerics, and it
   answers a model question, not the signal question. The user's stated
   priority is own-compute feasibility, now demonstrated on a smaller Qwen
   loop, so read Tinker here as the fallback that preserves comparability
   with the paper lineage; nothing in this review authorizes spend.
2. The dedicated GLM-5.3-Flash instance is already solved: job 24044573 has
   served it for 28 h on 2x B200 at TP=2 with MTP speculative decoding. Use
   it as sampler, baseline and harvest engine. Do not treat it as a trainer
   until (a) vLLM LoRA PR #56327 is merged or built, (b) a vision bridge
   exists in the Megatron trainer, and (c) a sampler/trainer logprob parity
   gate passes (Sec. 3.3).
3. The decisive scientific controls are: a continuous ground-truth positive
   control inside the evaluator pool with serial re-execution of timeouts
   (contention is a reward bias against longer-running programs, not just
   noise); `raw_iou` and a validity-only binary reward as known-failure and
   format controls; a signal-swap evaluation matrix plus topology agreement
   as signal-independent endpoints; at least 3 seeds with a pre-registered
   endpoint, margin and decision rule committed under sha256 before launch;
   and a bounded sampler/trainer KL for any self-hosted arm.
4. Before any GPU time: offline within-group rank agreement between the
   candidate signals on the re-scored recorded rollouts. GRPO sees only the
   within-group ranking and spacing of rewards. If the candidates agree with
   `shaped_v3b` on most group rankings, the RL comparison is underpowered by
   construction and the budget belongs to the environment axis (multi-turn
   visual feedback) or to data.
5. Power: F1-F8 cannot discriminate signals (per-target SD 0.129 at n=8, so a
   paired comparison detects about 0.15 IoU). Use the 646-row held-out
   representation split with 4 attempts per task as primary; seed variance,
   not evaluation size, will limit power, so plan 3 to 5 seeds.
6. Cluster blockers you will hit: `$HOME` is at 993k of 1,000k inodes and
   130 of 200 GB (any venv or pip install there will fail); pool has 521 GB
   free (the FP8 checkpoint fits, the 642 GB BF16 checkpoint does not); nodes
   report `TmpDisk=0` (rely on the 2 TB page cache); no Docker (Apptainer
   1.5.2); `mit_testing` has `PreemptMode=OFF` and a 7-day limit, but 3 of
   12 B200 nodes are reserved and other users have 20+ multi-node jobs queued.
7. Root's `extract_polygons` fix changes the verifier under the published
   record. Until the record and the canonical-policy re-scores are
   recomputed with the fixed function, no comparison against recorded
   numbers is valid (Sec. 2.7).

## 1. What I verified

### 1.1 Repository

- Reward and optimizer: `shaped_v3b` as documented; GRPO with
  `loss_fn=importance_sampling`, `kl_penalty_coef=0`,
  `remove_constant_reward_groups=True`, `rollout_error_tolerance=False`,
  rank-32 LoRA, lr 1e-5, G=8, B=8, T=1.0, 4,096 tokens, 30 steps per level.
- Batches are deterministic in `step` and `schedule_seed` (default 10,000),
  so arms that share the task pools see identical task sequences step for
  step. That makes a paired per-step analysis possible across arms.
- Validation canaries: 40 rows from the validation split (seed 7). Probe: the
  first 16 validation rows per level by sorted opaque id.
- Evaluator (`rl/common/evaluator.py`): subprocess tier by default, 20 s
  wall, 18 CPU-s rlimit, 4 GB address space, 8 workers unless
  `PIXCELL_EVAL_WORKERS` is set. `RUNTIME_TIMEOUT` is attributed to MODEL,
  rewarded 0 and never retried. Only `WORKER_ERROR` and `MEASUREMENT_ERROR`
  are EVALUATOR faults with up to 3 retries and then an abort. Metrics carry
  `chamfer_boundary_um` and both directional chamfers.
- Preflight runs a ground-truth positive control once at launch, not
  continuously during training.
- Dataset rows carry `topology_json`, `port_signature_json`,
  `primitive_calls`, `parameters_json` and `leakage_group_id`. That is a
  machine-checkable structural ground truth no training signal optimizes
  directly, and the grouping key for representation-disjoint splits.
  depth-v1 is 4,560 rows (3,468 train / 1,092 validation).
- Published noise levels (data/training/qwen-rl-v2 and
  `arxiv/scripts/fig_rl_assets/training_telemetry.json`): Run B benchmark
  per-target mean IoU SD 0.129 (n=8); probe (n=80) base to final mean IoU
  0.079 to 0.179 and executable rate 0.20 to 0.55; the post-L3 probe was
  contaminated by evaluation contention; training-batch IoU moves 0.06 to
  0.09 step to step.
- The July self-hosted loop at
  `/home/aadarwal/PixCell-running/rl/local/{grpo.py,rollouts.py,train_gemma.py}`
  on Engaging: vLLM sampler with a fresh `LoRARequest` per step, PEFT learner
  on language-model linear layers only with the vision tower frozen,
  token-level importance sampling with a CISPO-style ratio cap, bias-free
  group-mean advantages. Its own comment records measured bf16 engine versus
  trainer ratio tails of 20 to 45. Environment: torch 2.11.0, transformers
  5.13.0, peft 0.19.1. Cached models in `/orcd/scratch/orcd/010/aadarwal/pixcell/hf`:
  Qwen3-VL-30B-A3B-Instruct, gemma-4 12B/31B/E4B. I found no adapter or
  optimizer state under `PixCell-running` at depth 4; root's workers may
  have found it elsewhere.
- `homi.model_client` has no base-URL override in its OpenAI backend; the
  OpenAI SDK honors `OPENAI_BASE_URL` from the environment, so the chatbot
  harness can probably be pointed at the vLLM endpoint without code, but the
  model-id parsing for a served name like `contract-glm53-flash` is unverified.

### 1.2 Engaging (ssh read-only, 2026-10-04 about 22:50 ET)

- Groups: `orcd_rg_par_ou_orcd_testing` (grants `mit_testing` and
  `mit_user_testing`), `orcd_rg_shared_pi_englund`. Association
  `mit_general/normal`. The `mit_testing` QoS shows no TRES limits.
- `mit_testing`: 12 nodes of 8x B200, 224 CPUs, 2 TB RAM, `TmpDisk=0`,
  Rocky 8, plus one 8x B300 node. `MaxTime` 7 days, `PreemptMode=OFF`. At
  inspection: 6 idle (5600-5602, 5800-5802), 3 reserved (5700-5702), 2 mixed
  with our jobs (5501, 5502), 1 drained (5500). `mit_user_testing` is the
  subset 5500-5502 and 5700-5702, none idle.
- Our running jobs: `llm-glm-engaging` 24044573 (2x B200, 384 GB, node5501,
  28 h, successor 24763402 queued with `afterany`); `glm-cap0924-u/v/w`
  (three 2-GPU replicas on node5502, 2 d 22 h, more queued with
  `BeginTime`); `pixcell-contract-glm` 24879182 (2x B200, 30 min, node5501);
  `llm-inkling` (2x B200, 6 h chain on `mit_user_testing`, timing out and
  re-queueing every 6 h).
- GLM serving facts from the logs: `zai-org/GLM-5.3-Flash` revision
  `03eb5366...`, vLLM dev build `v0.1.dev20051+g487ecf187` inside the SIF
  (sha256 `87f6ab3d...`), TP=2, MTP speculative decoding with mean accepted
  length 2.38 to 2.39 and per-position acceptance 0.69/0.44/0.27 (three draft
  tokens), GPU KV cache 1,335,186 tokens at 262,144 max-model-len, weights
  load in 45 s from page cache, single-stream generation about 150 tok/s,
  prefill 7k to 14k tok/s, multimodal cache hit rate 77.9 % (image inputs
  are flowing).
- Smoke job 24879182 config: TP=2, fp8 KV, max-model-len 8,192,
  max-num-batched-tokens 4,096, max-num-seqs 2, `--enforce-eager`, one image
  per prompt, localhost:18153 with a per-run key, purpose "inference
  qualification; no optimizer or weight updates". Fine for qualification. As
  a rollout server its concurrency is capped at two sequences, so aggregate
  throughput cannot exceed about twice the observed single stream; the gain
  from a batch-64, CUDA-graph configuration is unmeasured.
- Storage: `$HOME` 130 G of 200 G and 993k of 1,000k files;
  `/orcd/pool/008/aadarwal` 1.0 T with 521 G free; `/orcd/pool/004/englund_shared`
  (group); scratch `/orcd/scratch/orcd/010/aadarwal` on a 294 T filesystem
  with 251 T free (purge policy not checked). The GLM FP8 snapshot and
  Inkling-Small-NVFP4 live in scratch `llm/hf`.
- Tooling: `apptainer/1.5.2` default, `cuda/12.9.1|13.0.1|13.1.0` modules, no
  vllm or sglang modules, no Docker.

### 1.3 External

- Tinker models page today: `GLM-5.3 (256K)` is text-only MoE at
  $4.86 / $12.15 / $14.58 per million tokens (prefill / sample / train);
  GLM-5.3-Flash is absent. Vision-capable entries: Inkling, Inkling-Small,
  four Nemotron 3.x models, Kimi-K2.6, Qwen3.8-27B, Qwen3.6-35B-A3B
  ($0.54 / $1.335 / $1.177), Qwen3.5-397B-A17B, Qwen3.5-9B, Qwen3.5-4B,
  Qwen3-8B. Qwen3-VL-235B and Qwen3-VL-30B were retired 2026-06-12.
  Checkpoint storage $0.10 per GB-month.
- vLLM recipe: FP8 checkpoint about 306 GiB, needs vLLM 0.29+ and FlashInfer
  0.6.17+, BF16 about twice that, an NVFP4 variant for Blackwell, MTP flag
  `--speculative-config '{"method":"mtp","num_speculative_tokens":N}'`.
- vLLM PR #56327 (LoRA for `Glm5NextForConditionalGeneration`): open as of
  2026-09-30. It maps the KDA six-way projection, the absorbed MLA
  projections, the vision tower qkv, MoE gate_up and lm_head. Follow-up
  #56718 fixed adapter application during prefill. verl end-to-end used it.
- SkyRL PR #2226 (Megatron GLM-5.3-Flash plus in-memory LoRA sync to vLLM):
  closed 2026-10-01 with the pieces merged separately, tested on two B300
  nodes, `language_model_only=true`, rank 32, NCCL weight sync, known
  wedge-on-failure issues. Root's workers confirm the trainer is
  language-only with the vision bridge pending.
- Architecture: 45 layers (34 KDA plus 11 MLA/DSA), mHC with four streams,
  320B total / 18B active (SkyRL counts 313B / 17B), one MTP layer, native
  vision encoder. The model card asks for images resized so the shorter
  side is at least 1.5K px, so PixCell's 1,440-px long-edge inputs may be
  upscaled into several thousand image tokens. Measure `prompt_tokens`.

## 2. Scientific controls

### 2.1 Evaluator integrity (your positive-control finding, extended)

Mechanism: a timeout is a MODEL fault with reward 0 and no retry. Under
contention (cold gdsfactory and kfactory imports take seconds, many
concurrent candidates, CPU shared with a sampler or trainer) this is a
systematic bias against programs that take longer to execute, which
correlates with complexity. The paper's post-L3 probe anomaly is the same
mechanism.

Controls:

- Inject at least one ground-truth program (the row's `code`) into every
  batch and score it through the same pool at the same concurrency. If its
  status is not OK or its IoU is below 0.99, mark the whole step as
  EVALUATOR-faulted, mask it, and halt. Your rule "positive-control failure
  stops any success claim" is right; make it per step, not per run.
- Any `RUNTIME_TIMEOUT` gets one serial re-execution on an idle core before
  it counts as MODEL. Only a second timeout is a model fault.
- Pin the evaluator pool to dedicated cores (cgroup or taskset) and request
  `--cpus-per-task` of at least twice the pool size. Never share cores with
  the vLLM engine or the trainer. The B200 nodes have 224 cores.
- Warm the pool (fork after importing the geometry stack) or let the 18 CPU-s
  rlimit be the binding budget with a generous wall timeout.
- Log latency per candidate and test afterwards that reward is uncorrelated
  with latency among OK results.
- Cross-machine determinism: compare `render_sha256` and IoU on a fixed
  corpus (the 80 probe ground truths plus the 8 champion programs in
  `data/training/qwen-rl-v2/agentloop`) between the release environment and
  the cluster environment before any claim. RC-01 T1 requires bit-identity
  across machines anyway.
- Isolation on the cluster: the Docker tier is unavailable. The strict AST
  gate plus rlimits is the tier the recorded campaign ran on, so it is
  acceptable. If you want a namespace boundary, test `unshare -Urn` or
  `apptainer exec --containall --net --network none` on a GPU node;
  unprivileged user namespaces on the Rocky 8 nodes are unverified.

### 2.2 Design of the comparison

- Compare signals within one model only. Never compare a signal trained on
  Qwen with one trained on GLM; the model effect dwarfs any signal effect.
  Consistency of the signal ranking across two models is the external
  validity check, done last.
- Hold everything but the reward fixed: base checkpoint, LoRA rank 32, lr
  1e-5, G=8, B=8, T=1.0, 4,096 tokens, 150 steps, the same curriculum and
  replay, the same `schedule_seed` (paired task sequences), the same
  evaluator image hash, prompt contract v3, and the same image preprocessing.
- Minimum arms: `shaped_v3b` (reference); `raw_iou` (known-failure control,
  expected to rediscover the rectangle attractor; if it does not, the setup
  lacks sensitivity or the attractor was model-specific); a validity-only
  binary reward (format control: it separates "learned to emit executable
  primitive programs" from "learned geometry"; the paper's 0 to 39 of 64
  executable jump is mostly format learning); each new candidate. Optional:
  `shaped_v3b` with the teacher weight set to 0, to test whether structural
  credit comes from the boundary term.
- Seeds: at least 3 per arm. Adaptive rule, pre-registered: run 3 seeds for
  all arms, then add seeds only to arms whose interval overlaps the leader.
- Pre-registration in the research-contracts style (RC-04 T1): commit arms,
  seeds, endpoints, margin, decision rule, analysis script, evaluator image
  hash and dataset digests, and record the sha256 before the first paid or
  GPU step. Decision rule: an arm beats the reference when the hierarchical
  bootstrap over tasks and seeds gives a 95 % interval for the primary delta
  that excludes 0, the delta is at least the pre-set margin (suggest 0.02
  IoU), and no anti-Goodhart metric worsens.

### 2.3 Endpoints (signal-independent)

- Primary: gate-recomputed raw IoU on the 646-row held-out representation
  split, 4 attempts per task at T=1.0, averaged over attempts then tasks.
  Co-primary: topology agreement against `topology_json` (component count,
  holes, ports), with one deterministic comparator shared by all arms.
  Secondary: executable rate, purity pass rate, Dice, boundary chamfer,
  best-of-4, F1-F8 single pass and agent-loop champion (transfer).
- Signal-swap matrix: score every arm's evaluation programs under every
  training signal. A policy that wins only under its own training signal is
  Goodharting.
- Anti-Goodhart diagnostics per arm over training: rectangle-attractor rate
  (OK results with `iou_n` below 0.05 and IoU above 0.5), program length and
  primitive count against the reference, within-group unique-program rate
  (collapse), sampled-token entropy, fraction length-capped, and
  `source_rejected` rate.
- Checkpoint policy: evaluate the final checkpoint and the fixed schedule
  (every 30 steps), never the best-by-evaluation checkpoint. Keep the 646
  split out of every gate; canaries and probes come only from the 846 split.

### 2.4 Power

- Run B per-target mean IoU has SD 0.129 at n=8, so a paired two-arm
  comparison on F1-F8 detects about 0.15 IoU at 80 % power. Signals will
  differ by 0.02 to 0.08. F1-F8 is a transfer sanity check, not the
  discriminator.
- 646 tasks x 4 attempts gives a task-clustered standard error near 0.01 per
  run. Seed-to-seed SD of GRPO runs is plausibly 0.02 to 0.04 (training-batch
  IoU noise is 0.06 to 0.09 per step), so seeds dominate. Three seeds give a
  minimum detectable effect around 0.05 to 0.07, five seeds around 0.04.
  These are planning estimates; replace the seed SD with the measured value
  once two seeds of any arm exist.

### 2.5 Zero-GPU prestudy (do this first)

- On the re-scored recorded rollouts (you already re-scored the three
  canonical policies), compute per group of 8 the Kendall tau and the argmax
  agreement between each candidate signal and `shaped_v3b`, restricted to
  groups with at least two OK candidates (GRPO drops constant groups).
  Report the distribution by level. If the median tau exceeds about 0.9 and
  argmax agreement exceeds about 85 %, the arms are near-identical for GRPO
  and the RL comparison should be deprioritized in favor of the environment
  axis (multi-turn visual feedback, where the agent loop's +0.07 IoU at
  deployment suggests the larger lever) or data.
- For the RC-01 adversarial constructions (bounding-box fill, merged and
  split features, moved ports), compute each signal's ordering against the
  honest counterpart. That is static T4 evidence with no training.

### 2.6 Controls specific to self-hosted arms

- Parity gate before step 1: on 256 sampled sequences, compare per-token
  logprobs between the vLLM sampler (FP8 base plus LoRA) and the trainer
  (BF16). Require mean absolute difference below about 0.05 nats and KL
  below about 1e-2, tuned first on Qwen where the loop exists. Log
  `kl_sampler_learner` and `ratio_max` every step and abort on drift. An FP8
  sampler against a BF16 trainer is a worse regime than Tinker's, and if it
  differs between arms it is a confound.
- Use the same truncated importance-sampling cap in every arm and record it.
- Keep the sampler at most one adapter behind the learner, and keep that lag
  identical across arms.

### 2.7 The `extract_polygons` fix changes the verifier under the record

Root reports a bug in the canonical polygon extraction (a child cell chosen
before the transformed root), now fixed with a regression test, which moved
one L1 ground truth from 0.068 to 0.9977. That function sits under
`homi.conductor.gate.recompute_metrics`, so the published record was
verified with the buggy version. Controls:

- Re-run the frozen record under the fixed function: every `data/agents/**`
  cell, the 8 champion programs in `data/training/qwen-rl-v2/agentloop`, the
  Run B benchmark programs if retained, and the dataset ground truths. Diff
  the IoUs. Any published number that moves is an erratum to record in a
  dated note beside the frozen record, never a silent patch.
- Every arm, the baseline arm and any recomputed Run B comparator must use
  the fixed verifier. Run B's recorded 0.228 / 0.467 / 0.491 are not
  comparable until recomputed.
- Re-score the canonical policies again after the fix. Rank-agreement
  numbers computed before it are void wherever transformed child cells occur.
- Training-signal consequence: programs built from transformed sub-cells
  earned near-zero reward under the old verifier, which may have pushed the
  released policy toward flat construction. Measure the share of affected
  programs in the recorded rollouts before interpreting Run B's behavior.

## 3. GLM-5.3-Flash: the honest trainer path

### 3.1 What exists today

- Inference is solved (TP=2 on 2x B200 with MTP). A rollout-grade server
  needs max-num-seqs of 64 or more, CUDA graphs (drop `--enforce-eager`),
  max-model-len near 16k after measuring prompt tokens, prefix caching (the
  catalog text is shared by every prompt), and `--enable-lora
  --max-lora-rank 32` with runtime adapter loading, which requires a build
  containing PR #56327.
- Training: no vision-capable RL trainer for this architecture is verified
  in the paths I inspected. SkyRL/Megatron is language-only; vLLM LoRA is an open PR; slime supports
  the GLM-5 family but the Flash vision path is unverified; ms-swift lists
  GLM-5.3 multimodal support but Megatron-SWIFT coverage of KDA and mHC is
  unverified; the HF-plus-PEFT design of the July loop cannot hold a 320B
  model usefully in eager mode.
- A "1x B200 optimizer proof" can only be Qwen3-VL-30B-A3B or Gemma 4. It is
  a plumbing proof for the Tinker-free loop and proves nothing about GLM
  memory, parallelism or numerics. Say so in the record.

### 3.2 Memory reality (8x B200, about 180 GB usable each, 2 TB host RAM)

- Full fine-tuning: optimizer state above 5 TB. Impossible.
- LoRA on a BF16 frozen base: arithmetic says 642 GB / 8 is about 80 GB per
  GPU for weights at EP=8, with LoRA parameters and Adam well under 5 GB.
  Treat that as an unverified capacity hypothesis, not a launch
  recommendation: the SkyRL two-node recipe
  (`run_dapo_glm5p3_flash_lora_sync_2node.sh`, cited in root's
  MODEL_FEASIBILITY.md) states that the EP=8 backward pass OOMs on B200 and
  uses EP=16 across two nodes; its single-node recipe is 8x B300. mHC's four
  residual streams and the MoE activation footprint are the likely reason
  my activation allowance was optimistic. Plan on two 8x B200 nodes (EP=16)
  or the one B300 node in `mit_testing` (node5900-c1, allocated at
  inspection). Either way it needs a Megatron-class trainer with KDA,
  MLA/DSA and mHC kernels, which is SkyRL's path.
- LoRA on an FP8 frozen base: 306 GiB / 8 is about 38 GB per GPU. Attractive
  but requires FP8 frozen-weight LoRA support in the trainer, unverified for
  this architecture.
- Colocating sampler and trainer: ruled out by the point above, since the
  trainer alone needs two B200 nodes. Disaggregate: the existing 2-GPU
  sampler job pattern plus a two-node EP=16 trainer job, with adapters
  synced over NCCL or the shared filesystem. A rank-32 adapter on attention and experts across 45
  layers is on the order of 1 to 3 GB; attention-only is hundreds of MB.
- Storage: the BF16 checkpoint (642 GB) does not fit in the pool's 521 GB
  free. Put it in scratch after checking the purge policy. Never in `$HOME`.

### 3.3 The one experiment that de-risks GLM training (duration unmeasured)

- Load GLM-5.3-Flash BF16 in SkyRL/Megatron with its two-node EP=16 B200
  recipe (or the single-node 8x B300 recipe) via the language-only path. Take 64 sequences sampled with images by the
  running vLLM instance. Precompute the frozen vision-tower and projector
  embeddings for those prompts with the HF implementation (deterministic,
  the dataset is frozen), inject them as input embeddings at the image-token
  positions, and compare trainer logprobs on the sampled tokens with vLLM's.
  Pass criterion as in 2.6. If the trainer cannot accept injected
  embeddings, the GLM vision-RL path is blocked until the vision bridge
  lands, and no GLM RL arm should be scheduled.
- Second gate: hot-load a LoRA adapter into the running vLLM (PR #56327
  build), sample, and compare logprobs with the trainer-plus-adapter. If
  this fails, the only alternative is merge, requantize to FP8 and reload
  306 GiB every step, which is not an honest on-policy loop.

### 3.4 What the dedicated instance is good for now

- Blind-agent and chatbot baselines of GLM-5.3-Flash on the tier suite and
  F1-F8 under frozen budgets, as an RC-04 candidate-registry entry.
- Harvest: verifier-approved GLM programs on the 3,068-row train split as a
  winner corpus for SFT or on-policy distillation into a smaller policy
  (Qwen3-VL-30B-A3B self-hosted, or Qwen3.6-35B-A3B on Tinker). That uses
  the instance productively and aligns with RC-04.
- The contract inference probe already running.

## 4. Tinker versus self-host, in numbers

Every figure in this section is an estimate from the published recipe and
public list prices, not a measurement. The user's priority is own-compute
feasibility; Tinker is the fallback that preserves comparability with Run B,
and nothing here authorizes spend.

- Tinker with Qwen3.6-35B-A3B, one 150-step run: 9,600 samples. Prefill
  about 3.5k tokens per sample (about 2.3k text plus image tokens; take the
  exact figure from the recorded `prompt_tokens` in any attempt ledger; the
  shared catalog prefix earns the 80 % cache discount), so 33.6M x $0.54 is
  about $18 or less. Sampled about 1.5k tokens x 9,600 = 14.4M x $1.335 is
  about $19. Training tokens about 48M x $1.177 is about $56. Roughly $95
  per run plus $5 to $10 of probes and evaluations. Four arms x three seeds
  is about $1.3k; adaptive extra seeds add about $0.5k. Set checkpoint TTLs
  (idle checkpoint storage cost about $6.8 per day in September).
- Self-hosted GLM: no marginal GPU cost, but (my guess) two to four
  engineer-weeks on unmerged paths, an unmeasured wall time per run on the
  two-node trainer plus the sampler, and no direct comparability with Run B
  because it is a different base model.
- Self-hosted Qwen3-VL-30B-A3B with the July loop: the realistic middle path
  if Tinker spend is unwanted (one B200 for the learner, one for the
  sampler), but it is a retired Tinker model and a different base than Run
  B, so comparability is lost again. The recommendation stands: Qwen3.6-35B-A3B
  on Tinker for the signal study.

## 5. Assumptions in the brief I would challenge

- "A single B200 cannot hold the FP8 weights": true (306 GiB against about
  183 GB) and irrelevant. TP=2 already works and is running; the binding
  constraint is the trainer.
- "Dedicated inference versus optimizer" is a false dichotomy for RL. Both
  are needed; the real choice is colocated versus disaggregated, and the
  answer is disaggregated (sampler job, trainer job, adapter sync).
- The regrouped 3,068 / 846 / 646 split over all 4,560 rows means Run B is
  not a drop-in baseline (its train set was the 3,468-row release split). A
  fresh `shaped_v3b` arm under the new split is the baseline.
- W&B is a mirror; the record is the artifact set plus evaluator JSON,
  re-scorable with `rl.common.evaluator`. Keep raw rollouts (program text,
  token ids, sampler logprobs). The July loop stores sampler logprobs; the
  Tinker path stores `raw_token_ids`.
- Image preprocessing parity: keep the input PNGs identical across arms and
  models, record `prompt_tokens`, and never tune resolution per arm. GLM's
  recommended 1.5K-px shorter side changes the visual budget relative to
  Qwen's 1,440-px long edge; document it and hold it fixed within GLM arms.
- The capacity-test replica pattern (three 2-GPU vLLM jobs per node) is
  right for serving but wrong for rollouts, which want one engine with a
  large batch and prefix cache rather than three small ones.

## 6. Suggested order for the next seven days

1. Zero-GPU prestudy (2.5) on the re-scored rollouts; publish the tau and
   argmax tables; decide whether RL arms are worth running.
2. Freeze protocol, splits, evaluator image and analysis script; commit and
   record the sha256. Add the per-step positive control and the serial
   timeout re-execution to the evaluator path every arm uses.
3. Launch `shaped_v3b`, `raw_iou`, validity-only and the candidate signal(s)
   x 3 seeds on the own-compute Qwen loop the user prefers (Tinker with
   Qwen3.6-35B-A3B is the fallback, about $1.3k by my estimate, unspent).
4. In parallel on Engaging: turn the smoke server into a rollout-grade GLM
   endpoint (CUDA graphs, max-num-seqs 64, prefix cache, measured prompt
   tokens); run GLM blind-agent baselines and the harvest.
5. GLM trainer go/no-go: the parity experiment in 3.3 on the SkyRL two-node
   EP=16 recipe, language-only Megatron plus injected vision embeddings; report the KL and
   whether LoRA hot-load works on the PR build.
6. Only after step 5 passes: one confirmation arm (winning signal versus
   `shaped_v3b`, two seeds) on GLM.
