# SWEEP STATE — FINAL_1..8 Phase A model matrix (resume anchor)
# Post-compaction conductor: read this + scratchpad sweep files, continue the queue.
# Scratchpad: /private/tmp/claude-501/-Users-aadarwal-src-QPG-MIT-homi/066923c8-b5ba-4f5a-9fe1-bc4603716b79/scratchpad

## RULES (user-mandated, binding)
- MAX 8 worker panes at a time. One wave = one model config = one NEW tmux window.
- Partial dirs from crashes: rm -rf and START FRESH.
- Readback gate before every brief (status line must show the config; haiku shows just "Haiku 4.5").
- "Stuck" = claude fires a command then sits in thinking forever. Watchdog: per-completion
  wake + 35min wave timeout -> kill hung panes, record HUNG, retry once in a cleanup wave.
- Conductor verifies EVERY cell on completion: recompute IoU (compare_absolute) + purity grep
  (gf.components stencils | add_polygon) -> append to scratchpad/sweep_verdicts.txt.
- Commit per wave: git -c commit.gpgsign=false. PHASE B IS FROZEN — Phase A only.
- Launch templates: claude --dangerously-skip-permissions --model <id> --effort <eff>;
  codex --yolo -c mcp_servers={} [-c model_reasoning_effort="<eff>"]
- Briefs: scratchpad/briefA_final{N}_{cfg}.md (render more from data/agents/paper_swap/briefs/phaseA_recreation.md)
- Watchdog script pattern: see scratchpad usage in session; memory guard <12% free aborts.

## VERIFIED DONE (conductor-checked IoU)
final1: opus48m 0.9473 (pilot) | codex55x 0.9491 (pilot)
final2: codex55x 0.9873 | codex55m 0.9601 | haiku45m 0.4388
final4: codex55x 0.9811
final5: codex55x 0.8458 | codex55m 0.9367  <- effort inversion
final6: codex55x 0.9393 | codex55m 0.8552
final7: codex55x 0.8632 | haiku45m 0.254 PURITY-VIOLATION (raw add_polygon x8)
final8: codex55x 0.9164

## WAVE QUEUE (execute in order, 8 max, new window each)
W1 haiku45m  RUNNING (waveH window): f1,f3,f4,f5,f6,f8 pending (f2,f7 done)
W2 opus45m   f1..f8 (8) — window waveO45
W3 opus48m   f2..f8 (7) — window waveO48 (f1 done in pilot)
W4 codex mixed: codex55x f3 + codex55m f1,f3,f4,f7,f8 (6) — window waveCX  [USER: codex before opus-max]
W5 codex55h  f1..f8 (8) — window waveCH (-c model_reasoning_effort="high")
W6 opus48max f1..f8 (8) — window waveOMX (crashed pre-results; fresh)
W7 sonnet45m f1..f8 (8) — window waveS45 (claude-sonnet-4-5, medium) [probed ok]
W8 sonnet5m  f1..f8 (8) — window waveS5  (claude-sonnet-5, medium) [probed ok]
W9 haiku45h  f1..f8 (8) — window waveHH  (haiku-4.5, effort HIGH — effort-rescue test vs W1)
W10 codex54m   f1..f8 (8) — window waveC54  (codex -m gpt-5.4, medium) [probed ok]
W11 codex54mini f1..f8 (8) — window waveC54M (codex -m gpt-5.4-mini, medium) [probed ok]
W12 codexspark f1..f8 (8) — window waveCSP  (codex -m gpt-5.3-codex-spark, medium) [probed ok]
  -> codex generation/tier ladder to mirror Claude's (spark/mini -> 5.4 -> 5.5), constant medium effort.
  -> readback strings: "gpt-5.4 medium", "gpt-5.4-mini medium", "gpt-5.3-codex-spark medium" (verify format on boot)
Then: final grid table, commit all results + transcripts archive, update user.
Readback strings: sonnet-4.5 -> "Sonnet 4.5"; sonnet-5 -> "Sonnet 5"; haiku high may not show effort — verify via /status if ambiguous, else accept "Haiku 4.5" + launched flag.
W13 codex56lunam GATED 8/8 (2026-07-27, host mbp): mean IoU .650, 0 violations, claims honest to 1e-6; wave wall ~13min; transcripts archived + access-audit clean
W14 codex56lunau GATED 8/8 (2026-07-27, host mbp): mean IoU 0.895, 0 purity hits; transcripts archived + audit clean
W15 codex56terram GATED 8/8 (2026-07-27, host mbp): mean IoU 0.826; transcripts archived + audit clean
W16 codex56solm GATED 8/8 (2026-07-27, host mbp): mean IoU 0.896; transcripts archived + audit clean
W17 codex56solx GATED 8/8 (2026-07-27, host mbp): mean IoU 0.914, 0 purity hits; transcripts archived + audit clean
W18 codex56terrau GATED 8/8 (2026-07-27, host mbp): mean IoU 0.900, 0 purity hits; transcripts archived + audit clean
W19 codex56solu GATED 8/8 (2026-07-27, host mbp): mean IoU 0.934, 0 purity hits; transcripts archived + audit clean
W20 codex56lunax GATED 8/8 (2026-07-27, host mbp): mean IoU 0.878, 0 purity hits; transcripts archived + audit 1 hits
W21 codex56terrax GATED 8/8 (2026-07-27, host mbp): mean IoU 0.902, 0 purity hits; transcripts archived + audit clean
W22 opus5m GATED 8/8 (2026-07-27, host mbp): mean IoU 0.940; transcripts archived + audit CLEAN (earlier 1-hit note traced to a prefix-collision mis-map; re-audit of correct transcripts: 0 hits)
W23 fable5m GATED 8/8 (2026-07-27, host mbp): mean IoU 0.952; transcripts archived + audit clean
W24 opus5max GATED 8/8 (2026-07-27, host mbp): mean IoU 0.955, 0 purity hits; transcripts archived + audit 1 hit — ruled INCIDENTAL (generic calibration-helper code via repo-grep of a foreign worktree; no device content; ruling in wave record)
W25 fable5max GATED 8/8 (2026-07-27, host mbp): mean IoU 0.974, 0 purity hits; transcripts archived + audit clean
