# RFP Intelligence Agent

AI-powered five-agent pipeline that transforms a raw RFP PDF into a populated, citation-grounded Word proposal draft in under 90 seconds — running entirely inside Microsoft 365.

## Track

- **🧠 Reasoning Agents** — built with Microsoft Foundry
- **Microsoft IQ layer:** Foundry IQ (knowledge-base-backed agentic retrieval)

Architecture decisions are locked in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## The Problem

Sales and BD teams spend 3–5 days on every RFP response, and win rates sit at 20–30% because proposals are generic. The relevant internal knowledge — past proposals, case studies, pricing, objections handled — is buried in SharePoint, Teams chats, and Outlook threads with no fast way to retrieve and apply it.

## The Solution

A six-stage reasoning pipeline built with Microsoft Foundry:

1. **Intake Agent** — parses the RFP with Azure AI Document Intelligence, extracts a structured requirement manifest (REQ-001, REQ-002…) with priority and category.
2. **Research Agent** — retrieves evidence for each requirement from a **Foundry IQ knowledge base** built over the company evidence corpus.
3. **Scorer Agent** — scores each requirement COVERED / PARTIAL / GAP and computes a priority-weighted win probability.
4. **Drafter Agent** — writes response sections that may cite only documents returned by retrieval; flags GAPs for human action.
5. **Verifier** — deterministic citation check: every citation must resolve to a retrieved document, or the claim is stripped and the section flagged.
6. **Review Agent** — produces the proposal DOCX with a Bid Decision Report appendix (the full per-requirement reasoning trace) and the human-approval Adaptive Card.

A Teams / Microsoft 365 Copilot entry point is on the deployment roadmap — not claimed as part of the live submission.

## Setup

```bash
git clone <repo-url>
cd rfp-intelligence-agent
cp .env.example .env
# Fill in .env with your Azure and M365 credentials
pip install -r requirements.txt
# Run in STUB mode (no live Azure credentials needed)
STUB_MODE=true python -m agents.orchestrator
# Run tests
pytest tests/
```

## Architecture

```
RFP PDF
  └─► Orchestrator (validated contracts between every stage)
        ├─► 1. Intake    — Azure AI Document Intelligence + Foundry model
        ├─► 2. Research  — ★ Foundry IQ knowledge base (agentic retrieval)
        ├─► 3. Scorer    — Foundry model + priority-weighted win probability
        ├─► 4. Drafter   — Foundry model, citations restricted to evidence map
        ├─► 5. Verifier  — deterministic citation verification (no LLM)
        └─► 6. Review    — proposal DOCX + Bid Decision Report + Adaptive Card
```

Full diagram and locked decisions: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## Microsoft Technologies Used

| Service | Purpose |
|---|---|
| Microsoft Foundry | Model inference for all reasoning stages |
| **Foundry IQ** | Knowledge base + agentic retrieval over the evidence corpus |
| Azure AI Document Intelligence | PDF/DOCX parsing (`prebuilt-layout`) |
| Microsoft Teams Adaptive Cards | Human-in-the-loop approval UX (rendered artifact) |

## Team

[Your name / team here]

## Demo

[DEMO VIDEO — to be added]
