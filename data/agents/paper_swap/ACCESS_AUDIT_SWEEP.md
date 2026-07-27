# Sweep access audit — 2026-07-03

Scope: all worker session transcripts for the FINAL_1..8 x 13-config sweep
(167 session files staged from: mini ~/.claude/projects, air ~/.claude/projects,
mini ~/.codex/sessions). Method: (1) pattern scan for forbidden-path strings;
(2) cross-cell reference check — any session whose first cell reference (its own
brief) differs from later cell references; (3) manual classification of every hit
(command + output context extracted from the transcript).

## Result

**No worker read another cell's answers or any forbidden benchmark/paper material.**
5 sessions contained cross-cell path strings; classification:

| Session (cell) | What happened | Classification |
|---|---|---|
| final2/codex55m | `ps` output while monitoring own run showed other workers' command lines | ambient, innocent |
| final4/codex55m | same (`ps -axo` + `lsof` on own PIDs) | ambient, innocent |
| final7/codex55m | same | ambient, innocent |
| final3/codex54mini | repo-wide `rg -n "extrude\("` for API usage examples returned single call-signature lines from sibling cells' device.py (other devices, same/other configs) | **hygiene caveat** — letter breach, not answer-seeking; own target never exposed; cell flagged in sweep_results.json, retained |
| codex rollout 01:01 | conductor-commissioned papers/provenance investigator (user-requested task), not a recreation worker; legitimately searched papers metadata | out of scope |

Conductor sessions legitimately reference all cells (verification) and are
excluded by construction.

## Notes
- The primitives-purity check is separate (source analysis per cell; see sweep_verdicts.txt).
- Claude workers technically have anu pane tools available; transcripts show zero pane-tool
  calls by any worker.
- Reproduce: experiments/paper_swap/tools/ + transcripts_staging/ (not committed; 233MB on disk,
  both hosts' copies retained).
