#!/bin/bash
# A bounded, private GLM inference qualification; submits no successor jobs.
set -euo pipefail
umask 077
ROOT=${1:?Pass the isolated remote experiment directory}
JOB=${SLURM_JOB_ID:?Run this script through sbatch}
ASSETS=/orcd/scratch/orcd/010/aadarwal/llm
REVISION=03eb5366286afd40d2221b1d9c63a6dd1ba4832e
PORT=${CONTRACT_PORT:-18153}
MAX_MODEL_LEN=${CONTRACT_MAX_MODEL_LEN:-8192}
RUN=$ROOT/runtime/$JOB
mkdir -p "$RUN" "$RUN/cache"/{vllm,inductor,triton}
if [ -n "${CONTRACT_WARM_CACHE:-}" ]; then
  # Seed only this experiment's compiler caches; never share writable caches
  # with another server or copy credentials from the runtime directory.
  case "$CONTRACT_WARM_CACHE" in
    "$ROOT"/runtime/*/cache) cp -a "$CONTRACT_WARM_CACHE/." "$RUN/cache/" ;;
    *) printf 'Warm cache must belong to this isolated experiment.\n' >&2; exit 2 ;;
  esac
fi
source /etc/profile.d/modules.sh 2>/dev/null || true
module load apptainer

# The owner's existing checksum record must still match the immutable assets.
python3 "$ASSETS/releases/glm-engaging-20260919/verify.py" --base "$ASSETS" --check-record
python3 - "$RUN" "$PORT" "$REVISION" "$MAX_MODEL_LEN" <<'PY'
import json, os, pathlib, secrets, socket, sys, datetime
run, port, revision = pathlib.Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
with socket.socket() as sock:
    sock.bind(('127.0.0.1', port))
(run / 'api-key').write_text(secrets.token_urlsafe(32))
metadata = dict(job_id=os.environ['SLURM_JOB_ID'], node=socket.gethostname(),
                port=port, served_model='contract-glm53-flash',
                model='zai-org/GLM-5.3-Flash', revision=revision,
                max_model_len=int(sys.argv[4]),
                image_sha256='87f6ab3d16ae98673bc4eba2e496a37e06cd67cdcab661e33171482e940950ae',
                cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES'),
                started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                purpose='inference qualification; no optimizer or weight updates')
(run / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
PY
nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv > "$RUN/gpus.csv"
scontrol show job "$JOB" > "$RUN/slurm.txt"
{
  printf 'VLLM_API_KEY=%s\n' "$(cat "$RUN/api-key")"
  printf 'HF_HOME=/model-hf\nHF_HUB_OFFLINE=1\n'
  printf 'XDG_CACHE_HOME=%s/cache\n' "$RUN"
  printf 'VLLM_CACHE_ROOT=%s/cache/vllm\n' "$RUN"
  printf 'TORCHINDUCTOR_CACHE_DIR=%s/cache/inductor\n' "$RUN"
  printf 'TRITON_CACHE_DIR=%s/cache/triton\n' "$RUN"
  printf 'CUDA_VISIBLE_DEVICES=%s\n' "${CUDA_VISIBLE_DEVICES:?No assigned GPUs}"
} > "$RUN/container.env"

SERVER=""
cleanup() {
  rc=$?
  trap - EXIT TERM INT
  if [ -n "$SERVER" ]; then kill "$SERVER" 2>/dev/null || true; wait "$SERVER" 2>/dev/null || true; fi
  rm -f "$RUN/container.env"
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 143' TERM INT

apptainer exec --nv --cleanenv --bind "$ROOT:$ROOT" --bind "$ASSETS/hf:/model-hf:ro" \
  --env-file "$RUN/container.env" "$ASSETS/images/vllm-glm53-flash.sif" \
  vllm serve "/model-hf/hub/models--zai-org--GLM-5.3-Flash/snapshots/$REVISION" \
  --host 127.0.0.1 --port "$PORT" --served-model-name contract-glm53-flash \
  --tensor-parallel-size 2 --kv-cache-dtype fp8 \
  --tool-call-parser glm47 --reasoning-parser glm45 --enable-auto-tool-choice \
  --max-model-len "$MAX_MODEL_LEN" --max-num-batched-tokens 4096 --max-num-seqs 2 \
  --limit-mm-per-prompt '{"image": 1, "video": 0}' \
  --enforce-eager --gpu-memory-utilization 0.95 > "$RUN/server.log" 2>&1 &
SERVER=$!
READY=0
for ((i=0; i<180; i++)); do
  if ! kill -0 "$SERVER" 2>/dev/null; then wait "$SERVER"; exit 1; fi
  if curl --silent --fail --max-time 2 "http://127.0.0.1:$PORT/health" >/dev/null; then READY=1; break; fi
  sleep 5
done
test "$READY" = 1
python3 "$ROOT/infra/probe_glm.py" --run-dir "$RUN"
printf 'Qualified endpoint at %s:127.0.0.1:%s; remains available until this bounded job ends.\n' "$(hostname)" "$PORT"
wait "$SERVER"
