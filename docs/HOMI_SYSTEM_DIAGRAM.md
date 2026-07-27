# PixCell System Architecture

> **Photonic Multimodal Intelligence** - Converting research papers into fabrication-ready GDS files. PixCell is the system (what you install); `homi` is its engine (what you import).

---

## Table of Contents

1. [Master Pipeline Overview](#1-master-pipeline-overview)
2. [Integration Layer Architecture](#2-integration-layer-architecture)
3. [Michaelangelo Engine](#3-michaelangelo-engine---gds-generation)
4. [JEE Engine](#4-jee-engine---parameter-optimization)
5. [MJ Engine](#5-mj-engine---paper-processing)
6. [Weber Engine](#6-weber-engine---script-analysis--device-workbench)
7. [Model Client Architecture](#7-model-client-architecture)
8. [MCP Server Layer](#8-mcp-server-layer)
9. [Calibration & Metrics System](#9-calibration--metrics-system)
10. [Project Structure](#10-project-structure)
11. [Data Flow Reference](#11-data-flow-reference)
12. [Complete Tool Reference](#12-complete-tool-reference)

---

## 1. Master Pipeline Overview

The complete end-to-end pipeline from research paper to simulation-ready GDS.

```mermaid
flowchart TB
    subgraph INPUT["📄 INPUT"]
        PDF[/"Research Paper<br/>(PDF)"/]
        DRAW[/"Manual Drawing<br/>(PNG/JPG)"/]
    end

    subgraph STEP1["Step 1: Upload"]
        UP[Upload Source]
        PROJ[(Project<br/>Directory)]
    end

    subgraph STEP2["Step 2: Select Device"]
        EXT[Extract Images<br/>from PDF]
        SCORE[Score Images<br/>for Device Content]
        SEL1[User Selects<br/>Best Device Image]
    end

    subgraph STEP3["Step 3: B&W Conversion"]
        GEN[Generate B&W<br/>Variants]
        REF[Refine with<br/>Custom Instructions]
        SEL2[Select Best<br/>B&W Variant]
    end

    subgraph STEP3_5["Step 3.5: Confirm Device"]
        CONF[Confirm Device<br/>& Extract Footprint]
    end

    subgraph STEP4["Step 4: Footprint"]
        GEM[Gemini Vision<br/>Extraction]
        CONFIRM[Confirm<br/>Dimensions]
    end

    subgraph STEP5["Step 5: GDS Generation"]
        P1[Phase 1:<br/>Multi-Seed Exploration<br/>5-41 seeds × 2 turns]
        P2[Phase 2:<br/>Extended Iteration<br/>3-8 additional turns]
        BEST[Select Best<br/>Result by IoU]
    end

    subgraph STEP5_5["Step 5.5: Optimization"]
        JEE_DEC{Enable JEE<br/>Optimization?}
        GRID[Grid Search]
        OPT[Powell +<br/>Nelder-Mead]
        APPLY[Apply Optimized<br/>Parameters]
    end

    subgraph STEP6["Step 6: Results"]
        GDS[/"best.gds<br/>best.py"/]
        VIS[Visualization &<br/>Metrics Display]
    end

    subgraph STEP7["Step 7: Workbench"]
        AST[AST Script<br/>Analysis]
        SLOTS[Generate<br/>Slot System]
        WBENCH[marimo Device<br/>Workbench]
    end

    subgraph STEP8["Step 8: Simulation"]
        TIDY[Tidy3D<br/>Configuration]
        CLOUD[Upload to<br/>Cloud]
        FDTD[FDTD<br/>Results]
    end

    %% Main Flow
    PDF --> UP
    DRAW --> UP
    UP --> PROJ
    PROJ --> EXT

    EXT --> SCORE
    SCORE --> SEL1

    SEL1 --> GEN
    GEN --> REF
    REF --> SEL2

    SEL2 --> CONF
    CONF --> GEM

    GEM --> CONFIRM

    CONFIRM --> P1
    P1 --> P2
    P2 --> BEST

    BEST --> JEE_DEC
    JEE_DEC -->|Yes| GRID
    JEE_DEC -->|No| GDS
    GRID --> OPT
    OPT --> APPLY
    APPLY --> GDS

    GDS --> VIS
    VIS --> AST
    AST --> SLOTS
    SLOTS --> WBENCH

    WBENCH --> TIDY
    TIDY --> CLOUD
    CLOUD --> FDTD

    %% Styling
    classDef input fill:#e1f5fe,stroke:#01579b
    classDef process fill:#fff3e0,stroke:#e65100
    classDef decision fill:#fce4ec,stroke:#880e4f
    classDef output fill:#e8f5e9,stroke:#1b5e20
    classDef engine fill:#f3e5f5,stroke:#4a148c

    class PDF,DRAW input
    class UP,EXT,SCORE,SEL1,GEN,REF,SEL2,CONF,GEM,CONFIRM process
    class JEE_DEC decision
    class GDS,VIS,FDTD output
    class P1,P2,GRID,OPT,AST,SLOTS,WBENCH,TIDY,CLOUD engine
```

### Pipeline Summary

| Step | Name | Engine | Key Output |
|------|------|--------|------------|
| 1 | Upload | - | `projects/{name}/paper.pdf` |
| 2 | Select Device | MJ | Scored device images |
| 3 | B&W Conversion | MJ | `device_bw.png` |
| 3.5 | Confirm Device | - | Extract footprint |
| 4 | Footprint | Gemini | `footprint.json` |
| 5 | GDS Generation | Michaelangelo | `best.gds`, `best.py` |
| 5.5 | Optimization | JEE | Optimized parameters |
| 6 | Results | - | Metrics visualization |
| 7 | Workbench | Weber | `homi explore` → marimo workbench |
| 8 | Simulation | Flex | Tidy3D cloud task |

---

## 2. Integration Layer Architecture

All business logic lives in `homi/`. The CLI (`homi.cli`), the studio (`homi.studio_app`), the device workbench (`homi.workbench`), and the MCP servers all import from here.

```mermaid
flowchart LR
    subgraph UI["🖥️ SURFACE LAYER"]
        CLI[homi CLI<br/>cli.py]
        STUDIO[homi studio<br/>studio_app.py]
        WB[Device Workbench<br/>workbench.py]
    end

    subgraph MCP["🔌 MCP SERVERS"]
        MJ_S[homi-mj]
        MICH_S[homi-michaelangelo]
        JEE_S[homi-jee]
        WEB_S[homi-weber]
        FLEX_S[homi-flex]
        PDK_S[homi-pdk]
        RAPH_S[homi-raphael]
    end

    subgraph HOMI["📦 INTEGRATION LAYER (homi/)"]
        PP[paper_processing.py]
        FE[footprint_extraction.py]
        GG[gds_generation.py]
        JI[jee_integration.py]
        WI[weber_integration.py]
        FI[flex_integration.py]
        MC[model_client/]
    end

    subgraph ENGINES["⚙️ ENGINE LAYER (src/)"]
        MICH[src/michaelangelo/core/]
        JEE_E[src/jee/core/]
        WEB_E[src/weber/core/]
        FLEX_E[src/flex/core/]
    end

    %% Surface connections
    CLI --> GG
    CLI --> JI
    CLI --> FI
    STUDIO --> WI
    WB --> WI

    %% MCP connections
    MJ_S --> PP
    MJ_S --> FE
    MICH_S --> GG
    JEE_S --> JI
    WEB_S --> WI
    FLEX_S --> FI
    RAPH_S --> GG

    %% Integration to Engine
    %% (paper processing is implemented directly in homi/paper_processing.py)
    GG --> MICH
    JI --> JEE_E
    WI --> WEB_E
    FI --> FLEX_E
    PP --> MC
    FE --> MC
    GG --> MC
```

### Integration Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `paper_processing.py` | ~500 | PDF extraction, scoring, B&W generation |
| `footprint_extraction.py` | ~400 | Dimension extraction from papers |
| `gds_generation.py` | ~900 | Orchestrate Michaelangelo Phase 1 & 2 |
| `jee_integration.py` | ~700 | Parameter optimization via SSE |
| `weber_integration.py` | ~500 | Explorer generation |
| `flex_integration.py` | ~200 | Tidy3D simulation |
| `model_client/` | ~400 | Unified 61-model API |

---

## 3. Michaelangelo Engine - GDS Generation

Multi-seed, multi-turn GDS generation with visual feedback loops.

### Phase 1: Multi-Seed Exploration

```mermaid
flowchart TB
    subgraph CONFIG["Configuration"]
        PRESET[/"Preset Selection<br/>quick|balanced|thorough|maximum"/]
        MODEL[/"Model Selection<br/>61 VLMs available"/]
        SEEDS[/"Seed Range<br/>base ± range"/]
    end

    subgraph SETUP["Setup"]
        COMP[Setup Component<br/>Directory]
        CAL[Generate<br/>Calibration]
        PROMPT[Load System<br/>Prompt]
    end

    subgraph PARALLEL["Parallel Execution (8-12 workers)"]
        direction TB
        S1[Seed 1333]
        S2[Seed 1334]
        S3[Seed 1335]
        SN[Seed N...]
    end

    subgraph TURN["Per-Seed Processing"]
        T1[Turn 1: Initial<br/>Generation]
        EXEC1[Execute<br/>GDSFactory Script]
        RAST1[Rasterize<br/>GDS to PNG]
        COMP1[Compare vs<br/>Target]
        T2[Turn 2: Refine<br/>with Visual Feedback]
        EXEC2[Execute<br/>Refined Script]
        RAST2[Rasterize<br/>Refined GDS]
        COMP2[Compute Final<br/>Metrics]
    end

    subgraph METRICS["Metrics Computed"]
        IOU[IoU: Intersection<br/>over Union]
        DICE[Dice<br/>Coefficient]
        SSE[Sum of Squared<br/>Errors]
    end

    subgraph RANK["Ranking"]
        SORT[Sort by IoU<br/>Descending]
        TOP[Select Top<br/>Seeds for Phase 2]
        SUMMARY[Save exploration_<br/>summary.json]
    end

    PRESET --> COMP
    MODEL --> COMP
    SEEDS --> COMP
    COMP --> CAL
    CAL --> PROMPT

    PROMPT --> S1
    PROMPT --> S2
    PROMPT --> S3
    PROMPT --> SN

    S1 --> T1
    S2 --> T1
    S3 --> T1
    SN --> T1

    T1 --> EXEC1
    EXEC1 --> RAST1
    RAST1 --> COMP1
    COMP1 --> T2
    T2 --> EXEC2
    EXEC2 --> RAST2
    RAST2 --> COMP2

    COMP2 --> IOU
    COMP2 --> DICE
    COMP2 --> SSE

    IOU --> SORT
    DICE --> SORT
    SSE --> SORT

    SORT --> TOP
    TOP --> SUMMARY
```

### Phase 2: Extended Iteration

```mermaid
flowchart TB
    subgraph INPUT["Phase 1 Results"]
        RESULTS[Top N Seeds<br/>from Phase 1]
        THRESH[SSE Threshold<br/>Filter]
    end

    subgraph ITER["Extended Iteration Loop"]
        LOAD[Load Best Script<br/>from Phase 1]

        subgraph TURNS["Additional Turns (3-8)"]
            T3[Turn 3]
            T4[Turn 4]
            T5[Turn 5]
            TN[Turn N...]
        end

        EARLY{SSE Increased<br/>2x Consecutive?}
        STOP[Early Stop]
        CONT[Continue]
    end

    subgraph BEST["Best Selection"]
        TRACK[Track Best<br/>Across ALL Turns]
        SELECT[Select by<br/>Lowest SSE]
        SAVE[Save to<br/>output/best.gds]
    end

    RESULTS --> LOAD
    THRESH --> LOAD
    LOAD --> T3
    T3 --> T4
    T4 --> T5
    T5 --> TN

    TN --> EARLY
    EARLY -->|Yes| STOP
    EARLY -->|No| CONT
    CONT --> TN

    STOP --> TRACK
    TN --> TRACK
    TRACK --> SELECT
    SELECT --> SAVE
```

### LLM Interaction Sequence

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant M as Model Client
    participant V as VLM (61 models)
    participant G as GDSFactory
    participant R as Rasterizer

    O->>M: create_client("gemini/gemini-3-flash-preview")
    M-->>O: (client, model_id)

    Note over O,V: Turn 1: Initial Generation
    O->>V: [System Prompt + Catalog + Target Image]
    V-->>O: GDSFactory Python Script
    O->>G: Execute Script
    G-->>O: device.gds
    O->>R: Rasterize GDS
    R-->>O: raster.png + metrics.json

    Note over O,V: Turn 2: Visual Feedback Refinement
    O->>V: [Previous Context + Raster PNG + "Improve this"]
    V-->>O: Refined GDSFactory Script
    O->>G: Execute Refined Script
    G-->>O: refined_device.gds
    O->>R: Rasterize Refined GDS
    R-->>O: refined_raster.png + metrics.json
```

### Generation Presets

| Preset | Seeds | Turns | Parallel | Typical Time |
|--------|-------|-------|----------|--------------|
| `quick` | 5 | 2 | 4 | ~5 min |
| `balanced` | 13 | 3 | 8 | ~10 min |
| `thorough` | 25 | 5 | 8 | ~20 min |
| `maximum` | 41 | 8 | 12 | ~40 min |

---

## 4. JEE Engine - Parameter Optimization

Two-phase optimization: Grid Search + Parallel Multi-Method.

### Optimization Pipeline

```mermaid
flowchart TB
    subgraph INPUT["Input"]
        SCRIPT[/"best.py<br/>(Parametric Script)"/]
        TARGET[/"device_bw.png<br/>(Target Image)"/]
        CALIB[/"calibration.json"/]
    end

    subgraph EXTRACT["Parameter Extraction"]
        AST[AST Parse<br/>Script]
        PARAMS[Extract Numeric<br/>Parameters]
        BOUNDS[Define<br/>Bounds]
    end

    subgraph BASELINE["Baseline Evaluation"]
        EXEC0[Execute with<br/>Original Params]
        SSE0[Compute<br/>Baseline SSE]
    end

    subgraph GRID["Phase 1: Grid Search"]
        CART[Cartesian Product<br/>5^N Points]
        EVAL[Evaluate Each<br/>Grid Point]
        RANK[Rank by<br/>Total Cost]
        TOPN[Select Top N<br/>Starting Points]
    end

    subgraph PARALLEL["Phase 2: Parallel Optimization"]
        direction LR
        subgraph W1["Worker 1"]
            P1_NM[Nelder-Mead<br/>from Point 1]
        end
        subgraph W2["Worker 2"]
            P1_PW[Powell<br/>from Point 1]
        end
        subgraph W3["Worker 3"]
            P2_NM[Nelder-Mead<br/>from Point 2]
        end
        subgraph W4["Worker 4"]
            P2_PW[Powell<br/>from Point 2]
        end
    end

    subgraph COST["Cost Function"]
        SSE[SSE:<br/>Pixel Errors]
        FP[Footprint<br/>Penalty]
        TOTAL[Total Cost =<br/>SSE + weight × FP]
    end

    subgraph OUTPUT["Output"]
        BEST_P[Best Parameters]
        IMPROVE[Improvement %]
        NEW_GDS[optimized.gds]
    end

    SCRIPT --> AST
    TARGET --> SSE0
    CALIB --> EVAL

    AST --> PARAMS
    PARAMS --> BOUNDS
    BOUNDS --> EXEC0
    EXEC0 --> SSE0

    SSE0 --> CART
    CART --> EVAL
    EVAL --> RANK
    RANK --> TOPN

    TOPN --> P1_NM
    TOPN --> P1_PW
    TOPN --> P2_NM
    TOPN --> P2_PW

    P1_NM --> SSE
    P1_PW --> SSE
    P2_NM --> SSE
    P2_PW --> SSE

    SSE --> TOTAL
    FP --> TOTAL

    TOTAL --> BEST_P
    BEST_P --> IMPROVE
    BEST_P --> NEW_GDS
```

### Cost Function Composition

```mermaid
flowchart LR
    subgraph PIXEL["Pixel-Level Error"]
        RASTER[Rasterize<br/>GDS]
        COMPARE[Compare vs<br/>Target]
        SSE_VAL["SSE = Σ(target - gds)²"]
    end

    subgraph FOOTPRINT["Footprint Penalty"]
        MEASURE[Measure GDS<br/>Bounding Box]
        EXCESS{Exceeds<br/>Target?}
        PEN_EX["exceed mode:<br/>penalty for excess only"]
        PEN_MATCH["match mode:<br/>penalty for any deviation"]
    end

    subgraph COMBINE["Combined Cost"]
        WEIGHT[/"Penalty Weight<br/>(default: 1.0)"/]
        TOTAL_COST["total_cost = SSE + weight × penalty"]
    end

    RASTER --> COMPARE
    COMPARE --> SSE_VAL

    MEASURE --> EXCESS
    EXCESS -->|Yes| PEN_EX
    EXCESS -->|No| PEN_MATCH

    SSE_VAL --> TOTAL_COST
    PEN_EX --> TOTAL_COST
    PEN_MATCH --> TOTAL_COST
    WEIGHT --> TOTAL_COST
```

### Optimization Methods Comparison

| Method | Type | Strengths | Best For |
|--------|------|-----------|----------|
| **Nelder-Mead** | Simplex | No gradients needed, robust | Non-smooth surfaces |
| **Powell** | Direction-set | Fast convergence | Smooth functions |
| **CMA-ES** | Evolution | Global search | Multi-modal problems |

---

## 5. MJ Engine - Paper Processing

PDF to B&W device image pipeline.

### Image Extraction & Scoring

```mermaid
flowchart LR
    subgraph INPUT["Input"]
        PDF[/"paper.pdf"/]
    end

    subgraph EXTRACT["Extraction"]
        FITZ[PyMuPDF<br/>fitz.open]
        IMAGES[Extract All<br/>Embedded Images]
        DEDUP[Deduplicate<br/>by MD5 Hash]
        FILTER[Filter<br/>> 5KB]
    end

    subgraph SCORE["Scoring"]
        GEMINI[Gemini Vision<br/>with Thinking]
        RANKED[Ranked List<br/>0-10 Scores]
    end

    subgraph SELECT["Selection"]
        AUTO[Auto-Select<br/>Best Device]
        USER[User<br/>Override]
        FINAL[Selected<br/>Device Image]
    end

    PDF --> FITZ
    FITZ --> IMAGES
    IMAGES --> DEDUP
    DEDUP --> FILTER

    FILTER --> GEMINI
    GEMINI --> RANKED

    RANKED --> AUTO
    AUTO --> USER
    USER --> FINAL
```

### B&W Variant Generation

```mermaid
flowchart TB
    subgraph INPUT["Selected Device"]
        DEVICE[/"device_image.png"/]
    end

    subgraph GENERATE["Gemini Image Generation"]
        PROMPT["Prompt: Create clean B&W<br/>silhouette, remove text,<br/>axes, colors, background"]
        MODEL[gemini-3-pro-image-preview]
        VARIANTS[Generate 5<br/>Variants]
    end

    subgraph REFINE["Optional Refinement"]
        INSTRUCT[/"Custom Instructions<br/>'remove circle on left'<br/>'sharpen waveguide edges'"/]
        REFINE_GEN[Generate 2<br/>Refined Variants]
    end

    subgraph SELECT["Selection"]
        GALLERY[Display<br/>Gallery]
        USER_SEL[User Selects<br/>Best Variant]
        SAVE[Save as<br/>device_bw.png]
    end

    DEVICE --> PROMPT
    PROMPT --> MODEL
    MODEL --> VARIANTS

    VARIANTS --> GALLERY
    VARIANTS --> INSTRUCT
    INSTRUCT --> REFINE_GEN
    REFINE_GEN --> GALLERY

    GALLERY --> USER_SEL
    USER_SEL --> SAVE
```

### Footprint Extraction

```mermaid
flowchart TB
    subgraph INPUT["Inputs"]
        PDF[/"paper.pdf"/]
        BW[/"device_bw.png"/]
    end

    subgraph GEMINI["Gemini Extraction"]
        TEXT[Extract PDF<br/>Text (10 pages)]
        VISION[Gemini Vision +<br/>Extended Thinking]
        PARSE_G[Parse μm<br/>Values]
    end

    subgraph MERGE["Validate"]
        VALIDATE[Validate Range<br/>0.01 - 10000 μm]
    end

    subgraph OUTPUT["Output"]
        FOOTPRINT[/"footprint.json<br/>{length_um, width_um}"/]
        USER_CONF[User<br/>Confirmation]
    end

    PDF --> TEXT
    BW --> VISION

    TEXT --> VISION
    VISION --> PARSE_G

    PARSE_G --> VALIDATE
    VALIDATE --> FOOTPRINT
    FOOTPRINT --> USER_CONF
```

---

## 6. Weber Engine - Script Analysis & Device Workbench

AST-based script analysis (`src/weber/core/`: `analyzer`, `config`, `default_slots`) feeding the marimo device workbench: `homi/weber_integration.py` turns a GDSFactory script into slot configuration and a live-knob schema, and `homi/workbench.py` emits a self-contained marimo notebook per device.

### Script Analysis Pipeline

```mermaid
flowchart TB
    subgraph INPUT["Input"]
        SCRIPT[/"best.py<br/>(GDSFactory Script)"/]
    end

    subgraph AST["AST Analysis (weber/core/analyzer.py)"]
        PARSE[ast.parse<br/>Source]
        VISITOR[GDSFactoryVisitor<br/>NodeVisitor]

        subgraph EXTRACT["Extraction"]
            FUNCS[Functions<br/>@gf.cell]
            PARAMS[Numeric<br/>Parameters]
            COMPS[gf.components.*<br/>Calls]
            LAYERS[Layer/Datatype<br/>Tuples]
            CONNS[".connect()<br/>Calls"]
        end
    end

    subgraph SLOTS["Slot Generation (weber/core/default_slots.py + config.py)"]
        GROUP[Group Related<br/>Parameters]
        SWAP[Identify<br/>Swappable Components]
        RANGES[Suggest<br/>Slider Ranges]
        CONFIG[SlotConfig<br/>Object]
    end

    subgraph OUTPUT["Workbench Feed (homi/)"]
        WI_N["weber_integration.py<br/>analyze_and_configure +<br/>get_live_parameter_info"]
        WBGEN["workbench.py<br/>generate_workbench"]
        NB["workbench.py notebook<br/>(marimo, per device)"]
    end

    SCRIPT --> PARSE
    PARSE --> VISITOR
    VISITOR --> FUNCS
    VISITOR --> PARAMS
    VISITOR --> COMPS
    VISITOR --> LAYERS
    VISITOR --> CONNS

    FUNCS --> GROUP
    PARAMS --> GROUP
    COMPS --> SWAP

    GROUP --> CONFIG
    SWAP --> CONFIG
    RANGES --> CONFIG

    CONFIG --> WI_N
    WI_N --> WBGEN
    WBGEN --> NB
```

### Swappable Component Groups

Defined in `weber/core/config.py` (`SWAP_GROUPS`) — only components with compatible parameter signatures are grouped:

```mermaid
flowchart LR
    subgraph SHAPES["shapes"]
        RC[rectangle]
        CIR[circle]
        ELL[ellipse]
        TRI[triangle]
    end

    subgraph BENDS_R["bends_radius"]
        BC[bend_circular]
        BE[bend_euler]
    end

    subgraph BENDS_S["bends_size"]
        BS[bend_s]
    end

    subgraph WAVEGUIDES["waveguides"]
        ST[straight]
        TP[taper]
    end

    RC <--> CIR
    CIR <--> ELL
    ELL <--> TRI

    BC <--> BE

    ST <--> TP
```

`bend_s` uses `size=(dx, dy)` and is not compatible with the radius-based bends, so it forms its own single-member group.

### The Device Workbench

`homi explore <script> [--launch]` writes `workbench.py` beside the script and serves it with marimo. The generated notebook imports only marimo/anywidget/gdsfactory/PIL/numpy — it stays dependency-free of the repo — and its fidelity readout is the same calibrated-raster IoU the conductor gate uses.

```mermaid
flowchart TB
    subgraph GEN["Generation (homi explore)"]
        BESTPY[/"best.py"/]
        SCHEMA[get_live_parameter_info<br/>live-knob schema]
        PROV["Gate provenance<br/>output/gate.json +<br/>recreation_* workdirs"]
        EMIT[generate_workbench]
    end

    subgraph NOTEBOOK["workbench.py (marimo)"]
        LT[Light Table<br/>mask + target overlay]
        KNOBS[Parameter Sliders<br/>live knobs]
        REBUILD[Rebuild Device<br/>via gdsfactory]
        IOUW["Live IoU<br/>(calibrated raster —<br/>same metric as the gate)"]
        EXPORT[Export GDS +<br/>handoff commands]
    end

    BESTPY --> SCHEMA
    SCHEMA --> EMIT
    PROV --> EMIT
    EMIT --> LT

    KNOBS --> REBUILD
    REBUILD --> LT
    REBUILD --> IOUW
    IOUW --> EXPORT
```

---

## 7. Model Client Architecture

Unified API for 61 vision-language models across 7 providers.

### Provider Backend Pattern

```mermaid
flowchart TB
    subgraph FACTORY["Factory Function"]
        CREATE["create_client(model_name)<br/>e.g., 'anthropic/claude-sonnet-4.5'"]
    end

    subgraph REGISTRY["Model Registry"]
        LOOKUP[Lookup in<br/>MODEL_REGISTRY]
        META[Get Metadata:<br/>provider, model_id,<br/>capabilities]
    end

    subgraph BACKENDS["Provider Backends"]
        GEM[GeminiBackend<br/>google.genai]
        CLAUDE[ClaudeBackend<br/>anthropic SDK]
        OAI[OpenAIBackend<br/>openai SDK]
        OR[OpenRouterBackend<br/>OpenRouter API]
    end

    subgraph INTERFACE["Unified Interface"]
        GEN["client.generate(<br/>  messages: List[VisionMessage],<br/>  config: ModelConfig,<br/>  model_id: str<br/>) -> GenerationResponse"]
    end

    CREATE --> LOOKUP
    LOOKUP --> META
    META -->|gemini/*| GEM
    META -->|anthropic/*| CLAUDE
    META -->|openai/*| OAI
    META -->|meta-llama/*<br/>moonshotai/*<br/>qwen/*<br/>x-ai/*| OR

    GEM --> GEN
    CLAUDE --> GEN
    OAI --> GEN
    OR --> GEN
```

### Core Types

```python
@dataclass
class ModelConfig:
    temperature: float = 1.0
    max_tokens: int = 16000
    seed: Optional[int] = None
    thinking_mode: Optional[str] = None  # "low"|"medium"|"high"
    thinking_budget: Optional[int] = None

@dataclass
class VisionMessage:
    role: str  # "user" | "assistant"
    text: str
    images: List[bytes]
    image_mime_types: List[str]

@dataclass
class GenerationResponse:
    text: str
    raw_response: Any
    usage: Optional[Dict[str, int]]
    thinking_content: Optional[str]
    model_id: Optional[str]
```

### Model Capability Matrix

| Provider | Models | Seed | Thinking | Vision | Max Tokens |
|----------|--------|------|----------|--------|------------|
| **Gemini** | 7 | Yes | Yes | Yes | 65K |
| **Claude** | 9 | No | Yes | Yes | 8K-64K |
| **OpenAI** | 10 | No | Yes | Yes | 16K |
| **Llama** | 4 | Yes | No | Yes | 16K |
| **Kimi** | 4 | Yes | Yes | Yes | 16K |
| **Qwen** | 20 | Yes | Some | Yes | 32K |
| **Grok** | 7 | Yes | Some | Yes | 8K-131K |

### Complete Model List

```mermaid
flowchart LR
    subgraph GEMINI["Google Gemini (7)"]
        G1[gemini-3.1-pro-preview]
        G2[gemini-3.1-flash-lite-preview]
        G3[gemini-3-flash-preview]
        G4[gemini-3-pro-preview]
        G5[gemini-2.5-flash]
        G6[gemini-2.5-pro]
        G7[gemini-2.0-flash-001]
    end

    subgraph CLAUDE["Anthropic Claude (9)"]
        C1[claude-opus-4.5]
        C2[claude-sonnet-4.5]
        C3[claude-haiku-4.5]
        C4[claude-opus-4]
        C5[claude-sonnet-4]
        C6[claude-3.7-sonnet]
        C7[claude-3.5-sonnet]
        C8[claude-3.5-haiku]
        C9[...]
    end

    subgraph OPENAI["OpenAI (10)"]
        O1[gpt-5.2]
        O2[gpt-5.2-pro]
        O3[gpt-5]
        O4[gpt-5-mini]
        O5[gpt-4o]
        O6[gpt-4.1]
        O7[...]
    end

    subgraph OPEN["OpenRouter (35)"]
        L1[llama-4-maverick]
        L2[kimi-vl-a3b-thinking]
        L3[qwen3-vl-235b-a22b]
        L4[grok-4]
        L5[...]
    end
```

---

## 8. MCP Server Layer

7 servers exposing 65 tools for Claude Code integration.

### Server Architecture

```mermaid
flowchart TB
    subgraph CLAUDE["Claude Code"]
        CC[Claude Code<br/>CLI/IDE]
    end

    subgraph SERVERS["7 MCP Servers"]
        subgraph MJ_SRV["homi-mj"]
            MJ_T["9 tools<br/>Paper Processing"]
        end

        subgraph MICH_SRV["homi-michaelangelo"]
            MICH_T["10 tools<br/>GDS Generation"]
        end

        subgraph JEE_SRV["homi-jee"]
            JEE_T["11 tools<br/>Optimization"]
        end

        subgraph WEB_SRV["homi-weber"]
            WEB_T["9 tools<br/>Script Analysis"]
        end

        subgraph FLEX_SRV["homi-flex"]
            FLEX_T["8 tools<br/>Simulation"]
        end

        subgraph PDK_SRV["homi-pdk"]
            PDK_T["12 tools<br/>PDK Mapping"]
        end

        subgraph RAPH_SRV["homi-raphael"]
            RAPH_T["6 tools<br/>Orchestrator"]
        end
    end

    subgraph HOMI["homi/ Integration"]
        INT[Integration<br/>Modules]
    end

    CC --> MJ_SRV
    CC --> MICH_SRV
    CC --> JEE_SRV
    CC --> WEB_SRV
    CC --> FLEX_SRV
    CC --> PDK_SRV
    CC --> RAPH_SRV

    MJ_T --> INT
    MICH_T --> INT
    JEE_T --> INT
    WEB_T --> INT
    FLEX_T --> INT
    PDK_T --> INT
    RAPH_T --> INT
```

### Async Task Pattern

```mermaid
sequenceDiagram
    participant C as Claude Code
    participant S as MCP Server
    participant T as Background Task

    C->>S: start_phase1_exploration()
    S->>S: create_task(task_id)
    S->>T: start_background_task()
    S-->>C: {task_id: "abc123"}

    loop Polling
        C->>S: poll_generation_status(task_id)
        S-->>C: {status: "running", progress: 45%}
    end

    T->>S: update_task(completed)
    C->>S: poll_generation_status(task_id)
    S-->>C: {status: "completed", results: {...}}

    C->>S: get_phase1_results()
    S-->>C: {ranked_seeds: [...]}
```

---

## 9. Calibration & Metrics System

Mapping between physical space (μm) and pixel space for accurate comparison.

### Calibration Pipeline

```mermaid
flowchart LR
    subgraph INPUT["Inputs"]
        BW[/"device_bw.png<br/>(target image)"/]
        FP[/"footprint.json<br/>{length_um, width_um}"/]
    end

    subgraph COMPUTE["Calibration Computation"]
        LOAD[Load Target<br/>Image]
        BBOX[Detect Device<br/>Bounding Box]
        SCALE[Compute Scale:<br/>px_per_um]
    end

    subgraph OUTPUT["calibration.json"]
        CAL["bbox: [x1, y1, x2, y2]<br/>bbox_size_px: [w, h]<br/>scale_px_per_um: [sx, sy]<br/>footprint_um: [l, w]<br/>image_size_px: [W, H]<br/>white_threshold: 245"]
    end

    BW --> LOAD
    FP --> SCALE
    LOAD --> BBOX
    BBOX --> SCALE
    SCALE --> CAL
```

### Scale Factor Calculation

```
scale_px_per_um[X] = bbox_width_px / length_um
scale_px_per_um[Y] = bbox_height_px / width_um
```

### Metric Computation

```mermaid
flowchart TB
    subgraph INPUT["Inputs"]
        TARGET[/"Target Image<br/>(device_bw.png)"/]
        GDS[/"Generated GDS"/]
        CAL[/"calibration.json"/]
    end

    subgraph RASTER["Rasterization"]
        EXTRACT[Extract Layer<br/>from GDS]
        RENDER[Render to<br/>Pixel Grid]
        ALIGN[Align to<br/>Calibration BBox]
    end

    subgraph BINARY["Binarization"]
        T_BIN[Binarize Target<br/>threshold=245]
        G_BIN[Binarize GDS<br/>threshold=245]
    end

    subgraph METRICS["Metrics"]
        subgraph PIXEL["Pixel Categories"]
            BB[Both Black<br/>True Positive]
            BW_[Both White<br/>True Negative]
            MB[Missing Black<br/>False Negative]
            EB[Extra Black<br/>False Positive]
        end

        IOU["IoU = TP / (TP + FP + FN)"]
        DICE["Dice = 2×TP / (2×TP + FP + FN)"]
        SSE_M["SSE = Σ(target - gds)²"]
        MSE["MSE = SSE / total_pixels"]
    end

    TARGET --> T_BIN
    GDS --> EXTRACT
    EXTRACT --> RENDER
    CAL --> ALIGN
    RENDER --> ALIGN
    ALIGN --> G_BIN

    T_BIN --> BB
    T_BIN --> BW_
    T_BIN --> MB
    T_BIN --> EB
    G_BIN --> BB
    G_BIN --> BW_
    G_BIN --> MB
    G_BIN --> EB

    BB --> IOU
    BW_ --> IOU
    MB --> IOU
    EB --> IOU

    BB --> DICE
    MB --> DICE
    EB --> DICE

    BB --> SSE_M
    BW_ --> SSE_M
    MB --> SSE_M
    EB --> SSE_M

    SSE_M --> MSE
```

### Metrics Reference

| Metric | Range | Primary Use | Formula |
|--------|-------|-------------|---------|
| **IoU** | 0-1 | Phase 1 Ranking | intersection / union |
| **Dice** | 0-1 | Phase 2 Refinement | 2×intersection / (pred + target) |
| **SSE** | 0-∞ | JEE Optimization | Σ(target_px - gds_px)² |
| **MSE** | 0-1 | Normalized Error | SSE / total_pixels |

---

## 10. Project Structure

Directory layout and artifact generation at each stage.

### Directory Tree

```
projects/{project_name}/
│
├── paper.pdf                          # Step 1: Source paper
│
├── extracted_images/                  # Step 2: All images from PDF
│   ├── page1_img1.png
│   ├── page1_img2.png
│   └── ...
│
├── bw_variants/                       # Step 3: B&W variants
│   ├── variant_1.png
│   ├── variant_2.png
│   └── ...
│
├── device_bw.png                      # Step 3: Selected B&W image
│
├── footprint.json                     # Step 4: Device dimensions
│
├── component/                         # Steps 5-6: Michaelangelo workspace
│   ├── component.png                  # Copy of device_bw.png
│   ├── footprint.json                 # Copy
│   ├── calibration.json               # Pixel↔physical mapping
│   ├── prompt.md                      # Generation system prompt
│   ├── iteration_prompt.md            # Refinement prompt
│   │
│   ├── phase1/                        # Multi-seed exploration
│   │   └── benchmark_{model}/
│   │       └── seed_results/
│   │           └── seed_{N}/
│   │               ├── turn_1/
│   │               │   ├── generated.py
│   │               │   ├── device.gds
│   │               │   ├── raster.png
│   │               │   └── metrics.json
│   │               └── turn_2/
│   │                   └── ...
│   │
│   ├── phase2/                        # Extended iteration
│   │   └── benchmark_{model}/
│   │       └── seed_results/
│   │           └── seed_{N}/
│   │               ├── turn_3/
│   │               ├── turn_4/
│   │               └── ...
│   │
│   └── results/
│       ├── multiturn_seeds/
│       │   └── exploration_summary.json
│       └── extended_iteration/
│           └── extended_exploration_summary.json
│
├── optimization_full/                 # Step 5.5: JEE optimization
│   ├── work/
│   │   ├── iteration_*.json
│   │   └── best_params.json
│   └── output/
│       ├── optimized.py
│       └── optimized.gds
│
├── output/                            # Step 6: Final results
│   ├── best.gds
│   ├── best.py
│   ├── summary.json
│   └── workbench.py                   # Step 7: homi explore (marimo workbench)
│
└── state.json                         # Project state persistence
```

### Artifact Generation Sequence

```mermaid
flowchart TB
    subgraph S1["Step 1"]
        A1[paper.pdf]
    end

    subgraph S2["Step 2"]
        A2[extracted_images/]
    end

    subgraph S3["Step 3"]
        A3a[bw_variants/]
        A3b[device_bw.png]
    end

    subgraph S4["Step 4"]
        A4[footprint.json]
    end

    subgraph S5["Step 5"]
        A5a[component/]
        A5b[calibration.json]
        A5c[phase1/]
        A5d[phase2/]
    end

    subgraph S5_5["Step 5.5"]
        A55[optimization_full/]
    end

    subgraph S6["Step 6"]
        A6a[output/best.gds]
        A6b[output/best.py]
    end

    subgraph S7["Step 7"]
        A7[output/workbench.py]
    end

    A1 --> A2
    A2 --> A3a
    A3a --> A3b
    A3b --> A4
    A4 --> A5a
    A5a --> A5b
    A5b --> A5c
    A5c --> A5d
    A5d --> A55
    A55 --> A6a
    A6a --> A6b
    A6b --> A7
```

---

## 11. Data Flow Reference

### Key Data Structures

| File | Format | Created At | Schema |
|------|--------|------------|--------|
| `footprint.json` | JSON | Step 4 | `{length_um: float, width_um: float}` |
| `calibration.json` | JSON | Step 5 setup | `{bbox, bbox_size_px, scale_px_per_um, footprint_um, image_size_px, white_threshold}` |
| `metrics.json` | JSON | Each turn | `{IoU, Dice, SSE, MSE, Accuracy, Precision, Recall, total_pixels, gds_size_um, size_match}` |
| `exploration_summary.json` | JSON | Phase 1 end | `{seed_results: [{seed, turn1_*, turn2_*, metrics}]}` |
| `state.json` | JSON | Throughout | `{step, timestamps, selections, paths}` |

### Stage-by-Stage Data Flow

| From | To | Data | Format |
|------|-----|------|--------|
| PDF | Extraction | Raw images | PNG |
| Images | Scoring | Scores | 0-10 float |
| Selected | B&W Gen | Variants | PNG |
| B&W + Paper | Footprint | Dimensions | μm values |
| B&W + Footprint | Calibration | Mapping | JSON |
| Calibration + Prompt | Phase 1 | GDS scripts | Python |
| Phase 1 | Phase 2 | Top seeds | Seed list |
| Phase 2 | JEE | Best script | Python |
| JEE | Output | Optimized | GDS + Python |
| Output | Weber | Workbench | marimo notebook |
| GDS | Flex | Simulation | Task ID |

---

## 12. Complete Tool Reference

### homi-mj (9 tools)

| Tool | Input | Output | Purpose |
|------|-------|--------|---------|
| `extract_images_from_pdf` | pdf_path, output_dir | List[{path, page, size}] | Extract embedded images, dedup by content hash |
| `generate_bw_variants` | image_path, num_variants | List[variant_paths] | Create B&W silhouettes via Gemini image generation |
| `refine_bw_image` | source_image_path, custom_instructions | List[refined_paths] | Refine a B&W image per custom instructions |
| `compute_image_similarity` | image1_path, image2_path | {SSIM, MSE, ...} | Compare two images |
| `get_image_metadata` | image_path | {dims, format, mode} | Image dimensions, format, color mode, size |
| `render_pdf_pages` | pdf_path, pages, scale | List[page_images] | Render full pages incl. vector graphics |
| `analyze_pdf_figures` | pdf_path | per-page counts + recommend_render | Per-page diagnostic, no API calls: embedded-image + vector-draw-op counts |
| `crop_region` | page_image_path, x1, y1, x2, y2 | cropped_image | Crop a region you located yourself, no API calls |
| `create_footprint_json` | length_um, width_um, output_path | footprint.json | Create footprint file for calibration |

### homi-michaelangelo (10 tools)

| Tool | Input | Output | Purpose |
|------|-------|--------|---------|
| `setup_component_directory` | image, output_dir, footprint | component/ dir | Initialize workspace |
| `run_calibration` | component_dir | calibration.json | Generate calibration |
| `start_phase1_exploration` | component_dir, preset, model | task_id | Start multi-seed |
| `poll_generation_status` | task_id | {status, progress} | Check progress |
| `get_phase1_results` | component_dir | ranked_seeds | Get Phase 1 results |
| `start_phase2_iteration` | component_dir, seeds | task_id | Start extended |
| `get_phase2_results` | component_dir | best_result | Get Phase 2 results |
| `get_generation_metrics` | component_dir | all_metrics | IoU/Dice for all seeds, diff images, rasters |
| `list_presets` | - | presets | Available generation presets |
| `list_available_models` | provider? | models | List all available models (61 across 7 providers) |

### homi-jee (11 tools)

| Tool | Input | Output | Purpose |
|------|-------|--------|---------|
| `extract_parameters` | script_path | List[{name, value, bounds}] | Find tunable numeric params + suggested bounds |
| `compute_sse` | target_image, raster_image | {SSE, MSE, RMSE} | Pixel error between target and rasterized GDS |
| `run_optimization` | script, target, calib, bounds | task_id | Start SSE minimization (long-running) |
| `poll_optimization` | task_id | {status, iteration, sse} | Check optimization progress |
| `get_optimization_result` | task_id | {best_params, improvement} | Final params, SSE, improvement % |
| `apply_parameters` | script, params | {script_path, gds_path} | Apply params, regenerate GDS |
| `prepare_calibration` | target_image, footprint_json | calibration.json | μm↔px mapping for SSE comparison |
| `get_optimization_config` | - | default config | Documented defaults (max_iterations, method, penalty) |
| `run_exploration` | script, target, calib | task_id | Grid search + parallel Powell/Nelder-Mead |
| `poll_exploration` | task_id | {status} | Check exploration progress |
| `get_exploration_result` | task_id | {best_result, comparison} | Best result across all methods |

### homi-weber (9 tools)

| Tool | Input | Output | Purpose |
|------|-------|--------|---------|
| `analyze_script` | script_path | ScriptAnalysis | AST parse: components, params, layers, functions |
| `detect_swappable_components` | analysis | swappable_groups | Find alternatives (e.g. bend_circular ↔ bend_euler) |
| `generate_slot_definitions` | analysis, output_path | slot_definitions.py | Semantic slot grouping of parameters |
| `validate_explorer` | app_path | {valid, errors} | Syntax/import check of generated code |
| `get_parameter_suggestions` | parameters | suggested_ranges | Slider ranges from values + photonics patterns |
| `build_device_with_params` | script, params | component info (+ GDS) | Execute script with injected slider values |
| `analyze_and_configure` | script_source or script_path | analysis + slot_config | Full analyzer → UI-ready slot configuration |
| `build_component_map` | slot_config | component_map | Slot IDs → component IDs for swapping |
| `build_device_slots_dict` | slot_config | device slots dict | Layer-assignment UI structure |

### homi-flex (8 tools)

| Tool | Input | Output | Purpose |
|------|-------|--------|---------|
| `is_tidy3d_available` | - | {available, version} | Check Tidy3D install |
| `get_material_presets` | - | List[presets] | Core/cladding refractive indices |
| `validate_api_key` | api_key | {valid} | Check authentication |
| `get_simulation_info` | gds_path | {layers, bounds} | Sim parameters without creating or uploading |
| `create_and_upload_simulation` | gds, api_key, material | {task_id, url} | Upload to cloud; returns Workbench URL |
| `run_parameter_sweep` | script, stack_json, sweep, fom, budget_fc | sweep results | Budgeted measure-only FDTD grid over declared tunables (dry_run preview) |
| `get_task_status` | task_id | {status} | queued / running / success / error |
| `get_workbench_url` | task_id | url | Tidy3D Workbench link |

### homi-pdk (12 tools)

| Tool | Input | Output | Purpose |
|------|-------|--------|---------|
| `analyze_paper_process` | paper_text or pdf_path | process_info | Extract thickness, materials, wavelength, foundry hints |
| `list_available_pdks` | - | List[pdks] | Available PDKs with specifications |
| `match_pdk` | process_info | ranked_matches | Compatible PDKs with confidence scores |
| `get_pdk_layer_mapping` | pdk_name | layer_map | Generic → PDK layers |
| `convert_to_pdk` | gds, pdk, output | converted.gds | Apply PDK layers |
| `run_drc` | gds, pdk | List[violations] | Design rule check with locations |
| `suggest_drc_fixes` | violations | List[suggestions] | Fix suggestions |
| `parse_pdk_document` | pdf_path | structured PDK definition | Layers, materials, cross-sections, rules from a foundry PDF |
| `load_builtin_pdk` | pdk_name | PDK definition | Load a pre-defined builtin PDK by name |
| `list_pdk_layers_full` | pdk_name | layer list | Complete material + geometry properties per layer |
| `get_layer_material_properties` | pdk_name, layer_name | material properties | Tidy3D-compatible indices for a PDK layer |
| `get_pdk_cross_sections` | pdk_name | cross-sections | Film/etch/slab thickness, sidewall angles |

### homi-raphael (6 tools)

| Tool | Input | Output | Purpose |
|------|-------|--------|---------|
| `setup_component_directory` | image, output, footprint | component/ | Initialize workspace |
| `run_calibration` | component_dir | calibration.json | Generate calibration |
| `execute_gds_script` | script_path | gds_path | Run GDSFactory script |
| `rasterize_and_compare` | gds, target, calib | {IoU, Dice, SSE} | IoU (the cost function) vs target |
| `get_gds_catalog` | extended? | catalog | GDSFactory function reference |
| `get_target_image` | component_dir | {image, footprint, calibration} | Get target info |

---

## Legend

### Diagram Symbols

| Symbol | Meaning |
|--------|---------|
| `[/text/]` | File/Data Input |
| `[text]` | Process/Action |
| `{text}` | Decision Point |
| `[(text)]` | Database/Storage |
| `((text))` | Circle: Start/End |

### Color Coding

| Color | Meaning |
|-------|---------|
| Blue | Input/Data |
| Orange | Processing |
| Pink | Decision |
| Green | Output |
| Purple | Engine/Core Process |

---

## Quick Reference

### Environment Variables

```bash
GEMINI_API_KEY=...        # Required for Gemini models
ANTHROPIC_API_KEY=...     # Required for Claude models
OPENAI_API_KEY=...        # Required for GPT models
OPENROUTER_API_KEY=...    # Required for Llama/Kimi/Qwen
TIDY3D_API_KEY=...        # Required for simulation
```

### Key Commands

```bash
# Launch the studio (chat front door + light table)
homi studio

# Generate + serve the device workbench for a script
homi explore projects/{name}/output/best.py --launch

# MCP servers: .mcp.json binds the console scripts
# (.venv/bin/homi-mj ... .venv/bin/homi-pdk, via gg.servers.entry_points)
.venv/bin/homi-mj

# the module form also works
.venv/bin/python -m gg.servers.mj_server
.venv/bin/python -m gg.servers.michaelangelo_server
.venv/bin/python -m gg.servers.raphael_server
.venv/bin/python -m gg.servers.jee_server
.venv/bin/python -m gg.servers.weber_server
.venv/bin/python -m gg.servers.flex_server
.venv/bin/python -m gg.servers.pdk_server
```

### Critical Dependencies

- **GDSFactory**: Pinned to 9.20.7 (9.3x+ has breaking API changes)
- **Python**: >=3.11,<3.14 required

---

*Generated for PixCell v1.0 (engine package: `homi`) - Photonic Multimodal Intelligence*
