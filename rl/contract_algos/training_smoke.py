"""Bounded, image-conditioned LoRA plumbing check on one CUDA GPU.

Uses only cached local weights. This is a two-example SFT optimizer smoke,
not a signal benchmark, a GRPO run, or evidence that GLM training works.
Heavy training dependencies are imported only after CLI validation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import time
from pathlib import Path


def completion_labels(prompt_ids: list[int], full_ids: list[int]) -> list[int]:
    """Fail closed if the chat template changes the training prompt prefix."""
    if not prompt_ids or full_ids[: len(prompt_ids)] != prompt_ids:
        raise ValueError("full conversation must preserve the exact processed prompt prefix")
    if len(full_ids) <= len(prompt_ids):
        raise ValueError("the example has no assistant completion tokens")
    return [-100] * len(prompt_ids) + full_ids[len(prompt_ids) :]


def is_attention_target(name: str) -> bool:
    """Intentionally restrict this pilot to language attention q/v projections."""
    return (
        ".layers." in name
        and name.endswith((".q_proj", ".v_proj"))
        and not any(
            marker in name.lower()
            for marker in ("visual", "vision", "projector", ".experts.", "audio")
        )
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--rank", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    if not 1 <= args.steps <= 10:
        parser.error("--steps must be between 1 and 10 for this bounded smoke")
    if not 1 <= args.rank <= 32:
        parser.error("--rank must be between 1 and 32")
    if not math.isfinite(args.learning_rate) or not 0 < args.learning_rate <= 1e-2:
        parser.error("--learning-rate must be finite and in (0, 0.01]")
    if not (args.model_path / "config.json").is_file():
        parser.error("--model-path must be an existing local model snapshot")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("--output-dir must be new or empty; existing results are preserved")
    return args


def run(args: argparse.Namespace) -> dict:
    import torch
    from peft import LoraConfig, PeftModel, get_peft_model
    from PIL import Image, ImageDraw
    from torch.nn import functional
    from transformers import AutoModelForImageTextToText, AutoProcessor

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("this smoke requires exactly one visible, allocated CUDA GPU")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.cuda.reset_peak_memory_stats()

    def emit(event: str, **values) -> None:
        row = {"event": event, "elapsed_seconds": time.monotonic() - start, **values}
        with (args.output_dir / "metrics.jsonl").open("a") as stream:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
        print(json.dumps(row, allow_nan=False), flush=True)

    metadata = {
        "model_path": str(args.model_path.resolve()),
        "snapshot_revision": args.model_path.name,
        "config_sha256": hashlib.sha256((args.model_path / "config.json").read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "gpu": torch.cuda.get_device_name(0),
        "gpu_total_bytes": torch.cuda.get_device_properties(0).total_memory,
        "cuda_version": torch.version.cuda,
        "packages": {
            package: importlib.metadata.version(package)
            for package in ("torch", "transformers", "peft", "accelerate", "safetensors")
        },
        "steps": args.steps,
        "rank": args.rank,
        "learning_rate": args.learning_rate,
        "seed": args.seed,
        "precision": "bf16 base, PEFT default adapter precision",
        "attention": "sdpa",
        "scope": "image-conditioned attention LoRA; frozen vision and MoE experts",
    }
    (args.output_dir / "config.json").write_text(json.dumps(metadata, indent=2) + "\n")
    emit("loading", **metadata)
    processor = AutoProcessor.from_pretrained(args.model_path, local_files_only=True)
    base = AutoModelForImageTextToText.from_pretrained(
        args.model_path,
        local_files_only=True,
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
        device_map={"": 0},
    )
    base.config.use_cache = False
    targets = [
        name
        for name, module in base.named_modules()
        if isinstance(module, torch.nn.Linear) and is_attention_target(name)
    ]
    if not targets:
        raise RuntimeError("no language attention targets found; unsupported model layout")
    model = get_peft_model(
        base,
        LoraConfig(
            r=args.rank, lora_alpha=args.rank, lora_dropout=0, bias="none", target_modules=targets
        ),
    )
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    trainable = {name: p for name, p in model.named_parameters() if p.requires_grad}
    if not trainable or any("lora_" not in name for name in trainable):
        raise RuntimeError("trainable parameters must consist only of LoRA adapters")
    frozen = {name: p for name, p in model.named_parameters() if not p.requires_grad}
    frozen_versions = {name: p._version for name, p in frozen.items()}
    initial = {name: p.detach().cpu().clone() for name, p in trainable.items()}
    emit(
        "loaded",
        trainable_parameters=sum(p.numel() for p in trainable.values()),
        target_count=len(targets),
    )

    # Two deterministic diagnostic images. They are not benchmark data.
    images = []
    for kind in ("red_square", "blue_circle"):
        img = Image.new("RGB", (256, 256), "white")
        draw = ImageDraw.Draw(img)
        if kind == "red_square":
            draw.rectangle((32, 64, 128, 160), fill="red")
        else:
            draw.ellipse((128, 64, 224, 160), fill="blue")
        img.save(args.output_dir / f"{kind}.png")
        images.append(img)
    prompt = "Name the colored shape in this image. Answer with its color and shape only."
    answers = ["red square", "blue circle"]
    examples = []
    for img, answer in zip(images, answers, strict=True):
        messages = [
            {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}
        ]
        prompt_text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        full_text = processor.apply_chat_template(
            messages + [{"role": "assistant", "content": [{"type": "text", "text": answer}]}],
            tokenize=False,
            add_generation_prompt=False,
        )
        prompt_batch = processor(
            text=prompt_text, images=[img], return_tensors="pt", add_special_tokens=False
        )
        batch = processor(
            text=full_text, images=[img], return_tensors="pt", add_special_tokens=False
        )
        labels = completion_labels(
            prompt_batch["input_ids"][0].tolist(), batch["input_ids"][0].tolist()
        )
        if "pixel_values" not in batch or not batch["pixel_values"].numel():
            raise RuntimeError("processor omitted image tensors")
        if batch["input_ids"].shape[1] > 512:
            raise RuntimeError("diagnostic example exceeds the 512-token smoke bound")
        batch = {key: value.to("cuda:0") for key, value in batch.items()}
        examples.append(
            (batch, torch.tensor([labels], device="cuda:0"), len(prompt_batch["input_ids"][0]))
        )
    if not torch.equal(
        examples[0][0]["input_ids"][:, : examples[0][2]],
        examples[1][0]["input_ids"][:, : examples[1][2]],
    ):
        raise RuntimeError("image dependence check requires identical prompt token IDs")

    def forward_loss(active_model, batch, labels):
        output = active_model(**batch, use_cache=False)
        selected = labels[:, 1:] != -100
        logits = output.logits[:, :-1][selected].float()
        expected = labels[:, 1:][selected]
        return functional.cross_entropy(logits, expected), output.logits

    def evaluate(active_model):
        active_model.eval()
        losses, first_token_logits = [], []
        with torch.no_grad():
            for batch, labels, prompt_len in examples:
                loss, logits = forward_loss(active_model, batch, labels)
                losses.append(float(loss))
                first_token_logits.append(logits[0, prompt_len - 1].float().cpu())
        return losses, first_token_logits

    before_losses, before_logits = evaluate(model)
    image_delta = float((before_logits[0] - before_logits[1]).abs().max())
    if not math.isfinite(image_delta) or image_delta <= 1e-6:
        raise RuntimeError("changing the image did not change next-token logits")
    emit("before", completion_losses=before_losses, image_logit_max_abs_delta=image_delta)
    optimizer = torch.optim.AdamW(list(trainable.values()), lr=args.learning_rate, weight_decay=0)
    for step in range(args.steps):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        step_loss = 0.0
        for batch, labels, _ in examples:
            loss, logits = forward_loss(model, batch, labels)
            if not torch.isfinite(loss):
                raise RuntimeError("nonfinite completion loss")
            step_loss += float(loss.detach()) / len(examples)
            (loss / len(examples)).backward()
            del loss, logits
        if any(p.grad is not None for p in frozen.values()):
            raise RuntimeError("a frozen base parameter received a gradient")
        grad_norm = float(
            torch.nn.utils.clip_grad_norm_(list(trainable.values()), 1.0, error_if_nonfinite=True)
        )
        if grad_norm <= 0:
            raise RuntimeError("no nonzero adapter gradient")
        optimizer.step()
        if any(p._version != frozen_versions[name] for name, p in frozen.items()):
            raise RuntimeError("a frozen parameter was modified in place")
        emit(
            "optimizer_step",
            step=step + 1,
            completion_loss=step_loss,
            grad_norm_before_clip=grad_norm,
        )
    optimizer.zero_grad(set_to_none=True)
    adapter_delta = max(
        float((p.detach().cpu() - initial[name]).abs().max()) for name, p in trainable.items()
    )
    if not math.isfinite(adapter_delta) or adapter_delta <= 0:
        raise RuntimeError("optimizer did not change adapter weights")
    after_losses, after_logits = evaluate(model)
    adapter_dir = args.output_dir / "adapter"
    model.save_pretrained(adapter_dir, safe_serialization=True)
    saved = {name: p.detach().cpu().clone() for name, p in trainable.items()}
    # Destroy the in-memory adapter, then reconstruct it from the saved files.
    # Reusing the untouched base avoids a second 60+ GB model load.
    base = model.unload()
    del model, optimizer, trainable, frozen
    torch.cuda.empty_cache()
    reloaded = PeftModel.from_pretrained(
        base, adapter_dir, is_trainable=False, local_files_only=True
    )
    for name, parameter in reloaded.named_parameters():
        if name in saved and not torch.equal(parameter.detach().cpu(), saved.pop(name)):
            raise RuntimeError(f"saved adapter tensor changed on reload: {name}")
    if saved:
        raise RuntimeError("adapter reload omitted saved trainable tensors")
    reload_losses, reload_logits = evaluate(reloaded)
    reload_delta = max(
        float((a - b).abs().max()) for a, b in zip(after_logits, reload_logits, strict=True)
    )
    if not math.isfinite(reload_delta) or reload_delta > 1e-4:
        raise RuntimeError(f"adapter reload changed predictions: max delta {reload_delta}")
    result = {
        "status": "passed",
        "training_performed": True,
        "scope": metadata["scope"],
        "optimizer_steps": args.steps,
        "completion_losses_before": before_losses,
        "completion_losses_after": after_losses,
        "completion_losses_reloaded": reload_losses,
        "image_logit_max_abs_delta": image_delta,
        "adapter_weight_max_abs_delta": adapter_delta,
        "reload_logit_max_abs_delta": reload_delta,
        "frozen_parameter_version_counters_unchanged": True,
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
        "elapsed_seconds": time.monotonic() - start,
        "limitations": "Two synthetic examples; no benchmark, convergence, GLM, or rollout-sync claim.",
    }
    (args.output_dir / "result.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )
    emit("complete", **result)
    return result


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        run(args)
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "result.json").write_text(
            json.dumps(
                {"status": "failed", "error_type": type(exc).__name__, "error": str(exc)}, indent=2
            )
            + "\n"
        )
        raise


if __name__ == "__main__":
    main()
