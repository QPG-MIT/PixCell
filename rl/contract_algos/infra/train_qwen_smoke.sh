#!/bin/bash
# Exactly one image-conditioned optimizer smoke; no successors or shared writes.
set -euo pipefail
umask 077
ROOT=${1:?Pass the isolated remote experiment directory}
JOB=${SLURM_JOB_ID:?Run this script through sbatch}
RUN=$ROOT/training/$JOB
PYTHON=/orcd/scratch/orcd/010/aadarwal/pixcell/envs/rl/bin/python
MODEL=/orcd/scratch/orcd/010/aadarwal/pixcell/hf/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct/snapshots/9c4b90e1e4ba969fd3b5378b57d966d725f1b86c
mkdir -p "$RUN/cache"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export PYTHONDONTWRITEBYTECODE=1
export HF_HOME="$RUN/cache/hf" XDG_CACHE_HOME="$RUN/cache"
export TORCHINDUCTOR_CACHE_DIR="$RUN/cache/inductor" TRITON_CACHE_DIR="$RUN/cache/triton"
export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 TOKENIZERS_PARALLELISM=false
nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv > "$RUN/gpus.csv"
scontrol show job "$JOB" > "$RUN/slurm.txt"
"$PYTHON" "$ROOT/infra/training_smoke.py" --model-path "$MODEL" \
  --output-dir "$RUN/result" --steps 1 --rank 4 --learning-rate 0.0001 --seed 7
