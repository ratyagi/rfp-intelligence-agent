# Architecture — locked decisions

This document is the single source of truth for what we are building for the
Agents League hackathon (deadline: June 14, 2026). Downstream work (corpus,
retrieval integration, refactor, README, demo) builds against this spec.
Changes here require an explicit decision, not drift.

## Track commitment

- **Track:** 🧠 Reasoning Agents — *Build with Microsoft Foundry*
- **Microsoft IQ layer (mandatory):** **Foundry IQ** — knowledge-base-backed
  agentic retrieval is the evidence layer for the entire pipeline.
- The Teams / Microsoft 365 Copilot entry point is **deployment roadmap**, not
  part of the submission's live surface. We do not claim it works.

**Why Reasoning Agents and not Enterprise Agents:** the Enterprise track
requires deploying into Microsoft 365 Copilot (licensed tenant, Copilot Studio
publishing). That cannot be made fully real by the deadline. The Reasoning
track is judged on multi-step reasoning built with Microsoft Foundry — which is
exactly what this pipeline is, and every part of it can be demonstrated live.

## The pitch (one sentence)

> An RFP reasoning pipeline that tells you whether you should bid, drafts a
> citation-grounded response from your real evidence base, and **proves** every
> citation — flagging exactly what it doesn't know instead of making it up.

## System diagram

```
RFP PDF
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ Orchestrator (sequential pipeline, validated contracts between   │
│ every stage, fail-soft with explicit partial states)             │
│                                                                  │
│  1. INTAKE      PDF → RequirementManifest                        │
│     Azure AI Document Intelligence (parse)                       │
│     + Foundry model (requirement extraction REQ-001…)            │
│                                                                  │
│  2. RESEARCH    RequirementManifest → EvidenceMap                │
│     ★ Foundry IQ knowledge base — agentic retrieval over the     │
│       indexed company evidence corpus (corpus/)                  │
│                                                                  │
│  3. SCORER      Manifest + EvidenceMap → ScoredManifest          │
│     Foundry model scores COVERED / PARTIAL / GAP per requirement │
│     + priority-weighted win probability (deterministic math)     │
│                                                                  │
│  4. DRAFTER     ScoredManifest + EvidenceMap → Draft sections    │
│     Foundry model writes per-requirement responses; may cite     │
│     ONLY documents present in the EvidenceMap                    │
│                                                                  │
│  5. VERIFIER    Draft → VerifiedDraft                            │
│     Deterministic code (no LLM): every citation must resolve to  │
│     a retrieved document; unresolvable claims stripped + flagged │
│                                                                  │
│  6. REVIEW      VerifiedDraft → proposal DOCX                    │
│                 + Bid Decision Report (reasoning trace appendix)  │
│                 + Adaptive Card JSON (rendered artifact)          │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
output/  → proposal .docx with verified citations, GAP flags,
           and the full per-requirement reasoning trace
```

## Locked decisions

### 1. Foundry IQ is the only retrieval layer

The previous Microsoft Graph search code (SharePoint / Teams / Outlook) is
**deleted**, not kept dormant. Evidence comes from a Foundry IQ knowledge base
built over `corpus/` — a set of realistic fictional company documents (past
proposals, case studies, certifications, pricing records). The hackathon's
"no confidential information" rule is also why the corpus is fictional.

Two retrieval modes behind **one interface** (`tools/retrieval.py`):

| Mode | `RETRIEVAL_MODE` | What it does |
|---|---|---|
| Foundry IQ (live/demo) | `foundry_iq` | Agentic retrieval against the Foundry IQ knowledge base |
| Local (dev/offline)    | `local`      | Keyword/BM25 ranking over `corpus/` on disk |

Both return the same shape: `[{doc_id, title, excerpt, source_path, score}]`.
The local mode is real retrieval over the same real corpus — not canned
responses — so the pipeline is honest in both modes. `STUB_MODE`'s hardcoded
fake evidence is removed.

### 2. The verifier is deterministic code, not another LLM

Citation verification is a trust mechanism; running it through a model would
reintroduce the failure mode it exists to catch. It checks that every
`[doc_id]` cited in a drafted section exists in the EvidenceMap for that
requirement, strips anything unresolvable, and downgrades the section
(COVERED → PARTIAL) with an explicit flag in the Bid Decision Report.

### 3. One Foundry client, validated contracts everywhere

- All model calls go through a single `tools/foundry_client.py` (the current
  copy-pasted `_call_foundry` ×4 is removed).
- Every inter-agent payload is a Pydantic model, validated at each boundary,
  with one retry on schema-invalid model output:
  `RequirementManifest`, `EvidenceMap`, `ScoredManifest`, `DraftedProposal`,
  `VerifiedProposal`.

### 4. Win probability is priority-weighted

`(Σ weight(req) × credit(score)) / Σ weight(req)` where weight is
high=3 / medium=2 / low=1 and credit is COVERED=1.0 / PARTIAL=0.5 / GAP=0.
A gap on a must-have requirement hurts more than a gap on a nice-to-have.
Deterministic math, computed in code — the model scores requirements, it does
not invent the probability.

### 5. Reasoning is a first-class output

Each requirement carries its decision chain: evidence considered → score and
why → confidence → what's missing. Rendered as the **Bid Decision Report**
appendix in the DOCX and streamed to the console during a run. The pipeline's
reasoning is shown, not asserted.

### 6. Cut from scope (roadmap only — see `docs/deployment-roadmap.md`, later)

- Microsoft Graph search (SharePoint / Teams / Outlook evidence sources)
- SharePoint upload of the approved draft
- Live Copilot Studio / Teams deployment and approval webhook polling
- The Adaptive Card is still **generated and rendered as a JSON artifact**
  (it demos the human-in-the-loop design) but is not posted to a live tenant.

### 7. Demo path

`python -m agents.orchestrator demo/sample_rfp.pdf` with `RETRIEVAL_MODE=foundry_iq`
and live Foundry credentials. The same command with `RETRIEVAL_MODE=local` must
also produce a complete, honest run for anyone cloning the repo without Azure
access. The demo video records the live mode.

## Environment variables (target state)

```
AZURE_FOUNDRY_ENDPOINT=      # Foundry project endpoint
AZURE_FOUNDRY_API_KEY=
FOUNDRY_MODEL_DEPLOYMENT=    # e.g. gpt-4o
FOUNDRY_IQ_KNOWLEDGE_BASE=   # knowledge base name/id
DOC_INTELLIGENCE_ENDPOINT=   # Azure AI Document Intelligence
DOC_INTELLIGENCE_KEY=
RETRIEVAL_MODE=local         # local | foundry_iq
OUTPUT_DIR=./output
```

`STUB_MODE`, all `AZURE_TENANT_ID`/Graph/SharePoint/Teams variables are removed.

## Rubric mapping

| Criterion | Where this architecture earns it |
|---|---|
| Accuracy & Relevance (20%) | Foundry IQ integration (mandatory ✓), built with Microsoft Foundry, real enterprise problem |
| Reasoning & Multi-step (20%) | 6-stage pipeline with visible per-requirement decision chains (Bid Decision Report) |
| Creativity (15%) | Bid/no-bid intelligence + deterministic citation verifier — "knows what it doesn't know" |
| UX & Presentation (15%) | One-command demo, streamed reasoning trace, polished DOCX output |
| Reliability & Safety (20%) | Citation verifier, schema-validated contracts, human-in-the-loop by design, no fake claims |
```
