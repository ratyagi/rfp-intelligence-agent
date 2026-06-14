# Sample output

A real, unedited run of the pipeline so you can see what it produces without
running it yourself.

- **`sample_dashboard.html`** — the human-facing results dashboard. Open it in
  any browser (no server needed). This is the demo's main visual.
- **`sample_proposal.docx`** — the drafted proposal, with the Bid Decision
  Report appended as an appendix (the full per-requirement reasoning trace).
- **`sample_bid_report.json`** — the machine-readable reasoning trace.
- **`sample_approval_card.json`** — the human-approval Adaptive Card payload.
- **`trace/`** — each agent's actual typed output for this run, stage by stage
  (`1_requirement_manifest` … `5_verified_proposal`). This is the per-stage
  reasoning trace the orchestrator writes on every run.

## Provenance of this run (June 14, 2026)

- **Input:** `demo/sample_rfp.pdf` (synthetic 8-page government cloud RFP)
- **Reasoning model:** Microsoft Foundry **gpt-4.1** (`MODEL_PROVIDER=foundry`)
- **Retrieval:** **Foundry IQ** / Azure AI Search index over `corpus/`
  (`RETRIEVAL_MODE=azure_search`)

| Metric | Value |
|---|---|
| Requirements extracted | 65 |
| COVERED / PARTIAL / GAP | 9 / 21 / 35 |
| Requirement coverage score | 33% |
| Citations verified (resolve to a retrieved document) | **68 / 68, 0 stripped** |
| Recommendation | REVIEW BID DECISION |
| Status | `complete`, 0 errors |

> ⚠️ **This is a proof-of-concept run on synthetic data.** Both the RFP and the
> evidence corpus are fictional and co-designed (see [`../corpus/README.md`](../corpus/README.md)).
> The figures demonstrate how the pipeline *behaves* — they are not a benchmark
> on unseen data. The many GAPs are the system working as intended: it flags
> requirements the corpus doesn't cover instead of inventing evidence.
