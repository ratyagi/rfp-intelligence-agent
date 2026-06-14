# RFP Intelligence Agent

A six-stage agentic pipeline that turns a raw RFP PDF into a citation-grounded draft proposal — where **every citation must resolve to an internal document that was actually retrieved for that requirement, or it gets stripped before the proposal ships**.

**Microsoft Agents League @ AI Skills Fest 2026 — 🧠 Reasoning Agents track · Microsoft IQ layer: Foundry IQ**

## The Problem

Sales and BD teams spend 3–5 days on every RFP response, and win rates sit at 20–30% because proposals are generic. The relevant internal knowledge — past case studies, certifications, pricing schedules, reference projects — is scattered across the organisation with no fast way to retrieve it, apply it, and *prove* it supports each claim. Worse, an LLM drafting a proposal unsupervised will happily invent capabilities the company doesn't have. A hallucinated claim in a signed government tender isn't an oops — it's a contract breach.

## The Solution

A pipeline that treats **citation provenance as the product**: multi-step reasoning extracts and scores requirements, retrieval supplies evidence with citation keys, and a deterministic verifier guarantees every surviving citation resolves to a document that was actually retrieved — anything else is stripped or withheld.

```mermaid
flowchart TD
    RFP[/"📄 RFP PDF / DOCX"/] --> S1

    subgraph PIPELINE["Six-stage pipeline — 3 LLM reasoning stages + 3 deterministic stages (orchestrator validates a Pydantic contract at every boundary)"]
        S1["1 · Intake 🧠 LLM (gpt-4.1)<br/>Azure AI Document Intelligence (pypdf fallback)<br/>→ RequirementManifest: REQ-001…REQ-NNN<br/>with priority + category"]
        S2["2 · Research ⚙️ retrieval, no LLM<br/>★ Foundry IQ knowledge retrieval<br/>(Azure AI Search index over evidence corpus)<br/>→ EvidenceMap: cited excerpts per requirement"]
        S3["3 · Scorer 🧠 LLM (gpt-4.1)<br/>judges COVERED / PARTIAL / GAP per requirement<br/>coverage score = deterministic priority-weighted math"]
        S4["4 · Drafter 🧠 LLM (gpt-4.1)<br/>writes sections that may cite ONLY<br/>retrieved [DOC-xxx] evidence"]
        S5["5 · Verifier ⚙️ deterministic, NO LLM<br/>every citation must resolve to retrieved evidence<br/>unresolvable → stripped · no valid citation → withheld as GAP"]
        S6["6 · Review ⚙️ assembly, no LLM<br/>proposal DOCX + Bid Decision Report<br/>+ human-approval Adaptive Card"]
        S1 --> S2 --> S3 --> S4 --> S5 --> S6
    end

    subgraph IQ["🧠 Microsoft IQ layer — Foundry IQ"]
        KB["Azure AI Search index<br/>(evidence corpus, doc_id citation keys;<br/>full-text on Free tier, semantic ranker on Basic+)"]
        AGENT["Foundry IQ knowledge agent<br/>(agentic query planning — roadmap;<br/>needs a model deployment)"]
        AGENT -. targets .-> KB
    end

    subgraph MODELS["Model inference — shared rate-limit-aware client"]
        FOUNDRY["★ Microsoft Foundry gpt-4.1<br/>(used in live demo)"]
        GHM["GitHub Models free tier<br/>(zero-cost fallback)"]
    end

    S2 <--> KB
    S1 & S3 & S4 <--> MODELS
    S6 --> OUT[/"📝 draft_proposal.docx · bid_report.json · approval_card.json"/]
    OUT --> HUMAN{"👤 Human approval gate<br/>nothing is sent anywhere<br/>without a person deciding"}
```

### Why this is a *reasoning* agent, not a wrapper

The pipeline has six stages. **Three are LLM reasoning stages** (Intake, Scorer, Drafter — all on gpt-4.1) and **three are deterministic stages with no LLM** (Research retrieval, Verifier, Review assembly). That split is the whole point: the LLM does the judgement, and plain code does the things you must be able to trust.

- **Multi-step decomposition** — an 8-page RFP becomes 40+ atomic requirements, each independently researched, scored, and drafted.
- **Judgement is separated from arithmetic** — the model judges evidence sufficiency per requirement; the requirement coverage score is deterministic priority-weighted math in code. The model never picks the final number and never decides whether to bid.
- **Adversarial self-checking** — the Verifier (stage 5) is deliberately *not* an LLM: citation verification is a trust mechanism, and running it through a model would reintroduce the failure mode it exists to catch.
- **A first-class reasoning trace** — the Bid Decision Report records the full decision chain per requirement (evidence considered → score + confidence → citation verification outcome → action required), streamed to the console, appended to the DOCX, and saved as JSON.

### What the Verifier does — and does not — guarantee

The Verifier checks that **every `[DOC-xxx]` citation in the drafted text resolves to a document that was actually retrieved for that requirement**, and strips any that don't (a section left with no valid citation is withheld as a GAP). So "51/51 citations verified" means *every citation points to a real retrieved source document* — not that an LLM-free check has confirmed the cited document fully proves the sentence. Claim-level fact-checking against excerpt content is on the roadmap; today the guarantee is provenance (no invented or cross-requirement citations), which is what stops the most dangerous failure mode — confident citations to documents that were never retrieved.

## Live run results (June 14, 2026 — fully on Microsoft Foundry, not stubbed)

Reasoning model: **Microsoft Foundry gpt-4.1** · Retrieval: **Foundry IQ** (Azure AI Search):

| Metric | Result |
|---|---|
| Requirements extracted from 8-page sample RFP | 68 |
| Scored | 6 COVERED · 18 PARTIAL · 44 GAP |
| Priority-weighted requirement coverage score | 25% |
| Citations verified by stage 5 | **51/51, 0 stripped** |
| Recommendation | REVIEW BID DECISION (deterministic band) |
| Pipeline status | `complete`, 0 errors |

The gaps are the system working as designed: requirements the evidence corpus genuinely doesn't cover (insurance schedules, timeline commitments, tender boilerplate) are flagged for human action instead of being papered over with confident prose. **Every one of the 51 citations the drafter produced resolved to a document that was actually retrieved for that requirement** (see *What the Verifier guarantees* above) — so no citation in the proposal points at an invented or un-retrieved source.

> ⚠️ The corpus and sample RFP are **synthetic and co-designed** as a proof of concept (see [`corpus/README.md`](corpus/README.md)) — the numbers above demonstrate the pipeline's behaviour, not benchmark performance on unseen data.

## Microsoft technologies used

| Service | Role |
|---|---|
| **Microsoft Foundry** (gpt-4.1) | Model inference for every reasoning stage — `MODEL_PROVIDER=foundry` |
| **Foundry IQ** (Azure AI Search) | Knowledge retrieval over the evidence corpus with citation keys — the Microsoft IQ layer |
| **GitHub Models** | Zero-cost inference fallback for environments without Foundry model quota |
| **Azure AI Document Intelligence** | RFP parsing, `prebuilt-layout` (pypdf fallback when no resource available) |
| **Adaptive Cards** | Human-in-the-loop approval artifact (Teams delivery is roadmap) |
| **GitHub Copilot / AI-assisted development** | Used throughout development |

## Engineering notes — running on a $0 budget

This project was built and demoed on free Azure subscriptions (a free trial and Azure for Students), with **no pay-as-you-go upgrade** — agent demos shouldn't require an uncapped credit card. Two design choices made that possible, both visible in the code:

1. **Inference** — `tools/foundry_client.py` serves two providers behind one interface. The live demo runs on a **Microsoft Foundry gpt-4.1 deployment** (`MODEL_PROVIDER=foundry`); **GitHub Models** is a drop-in zero-cost fallback (`MODEL_PROVIDER=github_models`) for anyone without Foundry model quota. The client is rate-limit aware: proactive tokens-per-minute pacing, `Retry-After` backoff, JSON mode with schema-validated retries.
2. **Retrieval** — `scripts/setup_foundry_iq.py` builds the complete Foundry IQ stack: Azure AI Search index → corpus upload → knowledge agent. The agentic knowledge agent needs an Azure OpenAI deployment for query planning; where that quota isn't available the script skips it and the pipeline queries **the same index directly** (`RETRIEVAL_MODE=azure_search`, semantic ranking when the tier supports it, full-text otherwise). The full agentic client (`FoundryIQRetriever`) is implemented and ready. The live demo runs against a real Azure AI Search index built from this corpus.

## Run it yourself

```bash
git clone https://github.com/ratyagi/rfp-intelligence-agent.git
cd rfp-intelligence-agent
pip install -r requirements.txt
cp .env.example .env   # then fill in the variables for your chosen mode

# Zero-credential smoke run (stubbed inference, local BM25 retrieval)
STUB_MODE=true RETRIEVAL_MODE=local python -m agents.orchestrator demo/sample_rfp.pdf

# Live run on the GitHub Models free tier (PAT with Models:read)
#   .env: MODEL_PROVIDER=github_models, GITHUB_MODELS_TOKEN=..., STUB_MODE=false
python -m agents.orchestrator demo/sample_rfp.pdf

# Foundry IQ retrieval (after creating an Azure AI Search resource)
python scripts/setup_foundry_iq.py     # builds index + uploads corpus (+ agent if you have model quota)
#   .env: RETRIEVAL_MODE=azure_search  (or foundry_iq with model quota)

# Tests (47, no credentials needed)
STUB_MODE=true RETRIEVAL_MODE=local python -m pytest tests/ -q
```

Each run writes three files to `output/` — the proposal DOCX (with the Bid Decision Report appendix), the bid report JSON, and the approval Adaptive Card JSON. **`output/` is gitignored**, so a fresh clone won't contain them — they appear only when you run the pipeline. A real, unedited example run is committed under [`samples/`](samples/) so you can see the output without running anything.

## Reliability & safety patterns

- Pydantic contracts validated at **every** stage boundary; schema-invalid model output is retried once with the validation error fed back, then handled fail-soft (skip chunk / score as GAP / withhold section).
- Deterministic citation verification — a citation that doesn't resolve to a retrieved document is stripped, and a section left with no valid citation is withheld as a GAP.
- Human approval gate — the pipeline produces artifacts; it never sends, posts, or submits anything itself.
- Rate-limit-aware client so the pipeline degrades to *slower*, not *broken*, on throttled free tiers.
- No secrets in the repo (`.env` is gitignored); the corpus and sample RFP are fully synthetic.

## Known limitations & roadmap

Stated plainly, because a tool that decides what evidence is sufficient has to be honest about its own boundaries:

- **Citation verification is provenance-level, not claim-level.** The Verifier confirms each citation resolves to a document that was retrieved for that requirement; it does not yet confirm the cited document's text actually supports the specific sentence. Claim-level grounding (semantic entailment against the excerpt) is the top roadmap item.
- **Proof of concept on synthetic data.** The corpus and RFP are fictional and co-designed; the pipeline has not been benchmarked on unseen real-world RFPs and corpora.
- **Coverage score ≠ win probability.** It is a priority-weighted requirement-coverage metric. It deliberately models nothing about price, competitors, incumbency, or evaluator preferences — the real determinants of a tender outcome.
- **Retrieval quality depends on the search tier.** On the Azure AI Search Free tier there is no semantic ranker, so retrieval is keyword/full-text and more sensitive to vocabulary mismatch; Basic tier (or the full Foundry IQ knowledge agent, which needs a model deployment) improves this.
- **Parsing.** The live demo uses a local pypdf fallback; Azure AI Document Intelligence (`prebuilt-layout`) is the documented higher-fidelity path and needs its own resource.

## Repository map

```
agents/          orchestrator + the six stage implementations
tools/           model client, retrieval (3 backends), contracts, DOCX/report/card builders
prompts/         system prompts (input/output contracts per agent)
corpus/          synthetic evidence corpus (DOC-001…DOC-014, front-matter citation keys)
samples/         a real committed run (proposal DOCX + bid report + approval card)
demo/            8-page sample RFP + demo script
scripts/         one-time Foundry IQ / Azure AI Search setup
tests/           47 tests, all runnable with zero credentials
docs/            ARCHITECTURE.md (locked decisions) + session notes
```

## Team

Rashi Tyagi ([@ratyagi](https://github.com/ratyagi))

## Demo video

[DEMO VIDEO — link to be added before submission]
