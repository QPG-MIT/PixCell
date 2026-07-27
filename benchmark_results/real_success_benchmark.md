# HOMI Benchmark: Real Success Rate Analysis

## The Problem with Raw IoU/SSE

A model can achieve high IoU using raw polygon vertices, but this output is **unusable**:
- Cannot sweep parameters (no `length`, `gap`, `radius` to tune)
- Cannot simulate in Tidy3D (no proper cross-sections)
- Cannot use Weber explorer (no parameters to generate sliders)
- Cannot use JEE optimizer (nothing to optimize)

**Therefore: Non-primitive outputs = FAILURES regardless of IoU score.**

## Metrics

| Metric | Description |
|--------|-------------|
| **Primitive Rate** | % of runs producing usable parametric scripts |
| **Success Rate** | % of runs with primitives AND IoU ≥ 0.5 |
| **Avg IoU (Usable)** | Mean IoU for primitive-based scripts only |
| **Expected Usable IoU** | `primitive_rate × avg_IoU` - combined quality metric |

## Categories

- **SUCCESS** (green): Uses primitives + IoU ≥ 0.5 → Ready for simulation
- **PARTIAL** (yellow): Uses primitives + IoU < 0.5 → Needs JEE optimization
- **FAILURE** (red): No primitives → Unusable, pipeline dead-end

## Results by Model

*Sorted by Expected Usable IoU (the metric that matters)*

| Rank | Model | Total | Success | Partial | Failure | Prim % | Exp. IoU |
|-----:|-------|------:|--------:|--------:|--------:|-------:|---------:|
| 1 | **Gemini-3-Pro** | 352 | 69 | 231 | 52 | 85.2% | **0.354** |
| 2 | **Gemini-3-Flash** | 323 | 47 | 170 | 106 | 67.2% | **0.276** |
| 3 | **Grok-4** | 147 | 13 | 68 | 66 | 55.1% | **0.186** |
| 4 | **Gemini-2.5-Flash** | 152 | 3 | 82 | 67 | 55.9% | **0.170** |
| 5 | **Gemini-2.5-Pro** | 187 | 0 | 102 | 85 | 54.5% | **0.106** |
| 6 | **Qwen-VL-Instruct** | 164 | 0 | 80 | 84 | 48.8% | **0.082** |
| 7 | **Claude-Opus-4.5** | 48 | 0 | 13 | 35 | 27.1% | **0.070** |
| 8 | **Gemini-2.0-Flash** | 172 | 1 | 51 | 120 | 30.2% | **0.063** |
| 9 | **Claude-Sonnet-4.5** | 67 | 1 | 8 | 58 | 13.4% | **0.031** |

## Detailed Breakdown

| Model | Prim Rate | Avg IoU (Prim) | Avg IoU (Fail) | Delta |
|-------|----------:|---------------:|---------------:|------:|
| Gemini-3-Pro | 85.2% | 0.415 | 0.671 | -0.256 |
| Gemini-3-Flash | 67.2% | 0.411 | 0.518 | -0.106 |
| Grok-4 | 55.1% | 0.337 | 0.458 | -0.121 |
| Gemini-2.5-Flash | 55.9% | 0.305 | 0.429 | -0.124 |
| Gemini-2.5-Pro | 54.5% | 0.194 | 0.371 | -0.177 |
| Qwen-VL-Instruct | 48.8% | 0.167 | 0.232 | -0.065 |
| Claude-Opus-4.5 | 27.1% | 0.258 | 0.419 | -0.160 |
| Gemini-2.0-Flash | 30.2% | 0.208 | 0.259 | -0.052 |
| Claude-Sonnet-4.5 | 13.4% | 0.233 | 0.319 | -0.086 |

## Stacked Bar Data (for visualization)

```
Model                  | Success | Partial | Failure | Total
-----------------------|---------|---------|---------|------
Gemini-3-Pro           |  19.6%  |  65.6%  |  14.8%  | ███▓▓▓▓▓▓▓▓▓▓▓▓▓░░
Gemini-3-Flash         |  14.6%  |  52.6%  |  32.8%  | ██▓▓▓▓▓▓▓▓▓▓░░░░░░
Grok-4                 |   8.8%  |  46.3%  |  44.9%  | █▓▓▓▓▓▓▓▓▓░░░░░░░░
Gemini-2.5-Flash       |   2.0%  |  53.9%  |  44.1%  | ▓▓▓▓▓▓▓▓▓▓░░░░░░░░
Gemini-2.5-Pro         |   0.0%  |  54.5%  |  45.5%  | ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░
Qwen-VL-Instruct       |   0.0%  |  48.8%  |  51.2%  | ▓▓▓▓▓▓▓▓▓░░░░░░░░░░
Claude-Opus-4.5        |   0.0%  |  27.1%  |  72.9%  | ▓▓▓▓▓░░░░░░░░░░░░░░
Gemini-2.0-Flash       |   0.6%  |  29.7%  |  69.8%  | ▓▓▓▓▓░░░░░░░░░░░░░
Claude-Sonnet-4.5      |   1.5%  |  11.9%  |  86.6%  | ▓▓░░░░░░░░░░░░░░░░░
```

Legend: █ Success (ready) | ▓ Partial (needs JEE) | ░ Failure (unusable)

## Key Findings

1. **Gemini-3-Pro** leads with 85.2% usable outputs and Expected IoU of 0.354
2. **Claude-Sonnet-4.5** has only 13.4% usable outputs - 58 of 67 runs are failures

### The Misleading IoU Problem

These models achieve HIGHER IoU when using polygons (failures) than primitives:

- **Gemini-3-Pro**: Failure IoU (0.671) > Primitive IoU (0.415)
- **Gemini-3-Flash**: Failure IoU (0.518) > Primitive IoU (0.411)
- **Grok-4**: Failure IoU (0.458) > Primitive IoU (0.337)
- **Gemini-2.5-Flash**: Failure IoU (0.429) > Primitive IoU (0.305)
- **Gemini-2.5-Pro**: Failure IoU (0.371) > Primitive IoU (0.194)
- **Qwen-VL-Instruct**: Failure IoU (0.232) > Primitive IoU (0.167)
- **Claude-Opus-4.5**: Failure IoU (0.419) > Primitive IoU (0.258)
- **Gemini-2.0-Flash**: Failure IoU (0.259) > Primitive IoU (0.208)
- **Claude-Sonnet-4.5**: Failure IoU (0.319) > Primitive IoU (0.233)

This shows why raw IoU is a misleading metric - the 'better' scores are unusable!

## Grok-4 vs Qwen-VL-Instruct

| Metric | Grok-4 | Qwen-VL-Instruct |
|--------|-------:|-----------------:|
| Primitive Rate | 55.1% | 48.8% |
| Success Rate | 8.8% | 0.0% |
| Avg IoU (Usable) | 0.337 | 0.167 |
| Expected Usable IoU | **0.186** | **0.082** |
| Failure Count | 66/147 | 84/164 |