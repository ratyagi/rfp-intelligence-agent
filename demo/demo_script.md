# Demo video script — RFP Intelligence Agent (≤5 min)

**Audience:** Agents League / Microsoft judges
**What this demo actually is:** a command-line run of the six-stage pipeline on
Microsoft Foundry (gpt-4.1) + Foundry IQ (Azure AI Search), producing a Word
proposal, a bid report, and an approval card. No SharePoint/Teams posting — the
human-approval step produces artifacts; delivery into Teams is roadmap.

> Timing note: a full live run takes ~6 minutes (free-tier pacing). Either
> pre-record the terminal and narrate over it (speed up the quiet stretches),
> or run live and cut the wait. The committed `samples/` files are your safe
> fallback to show the output.

## Before recording

- [ ] `.env` set to `MODEL_PROVIDER=foundry`, `RETRIEVAL_MODE=azure_search`, `STUB_MODE=false`
- [ ] Terminal open in the repo; font size up
- [ ] `samples/sample_proposal.docx` open in Word (fallback / for the output walk-through)
- [ ] The README open to the architecture diagram
- [ ] Azure portal open showing the Foundry gpt-4.1 deployment + the AI Search resource (proof it's real)

---

## [0:00–0:30] The problem

> "Responding to a government RFP takes a sales team 3–5 days: read every
> requirement, dig through past projects for evidence, and write each section.
> And if an AI drafts it unsupervised, it invents capabilities the company
> doesn't have — in a signed tender, that's a contract breach. So the hard part
> isn't writing. It's making every claim provably trace to a real document."

## [0:30–1:00] The architecture (show the README diagram)

> "This is a six-stage pipeline. Three stages use Microsoft Foundry gpt-4.1 to
> reason — extract requirements, score them, draft responses. Three stages are
> deterministic code with no LLM — retrieval from Foundry IQ, citation
> verification, and document assembly. The split is the point: the model
> judges; plain code does the things you have to be able to trust."

Briefly show the Azure portal: the gpt-4.1 deployment and the Azure AI Search
resource. "Both Microsoft layers are real and live."

## [1:00–3:30] Run it (narrate the logs as they scroll)

Run:
```bash
python -m agents.orchestrator demo/sample_rfp.pdf
```

Point to each stage as it logs:
1. **Intake** — "It's pulling every requirement out of an 8-page RFP — here, 59 of them."
2. **Research** — point to `REQ-xxx — N evidence item(s) [DOC-...]` lines and a `(no corpus coverage)` line: "For each requirement it queries our Foundry IQ knowledge base. Notice some return nothing — it's honest about what the evidence base doesn't cover."
3. **Scorer** — "gpt-4.1 judges each: COVERED, PARTIAL, or GAP."
4. **Verifier** — point to `52/52 citations verified, 0 stripped`: **"This is the heart of it. Every citation the drafter wrote is checked against what was actually retrieved. Anything that doesn't resolve is stripped. Nothing invented survives."**
5. Final `status: complete` JSON with the coverage score.

## [3:30–4:30] The output (open the DOCX)

> "Here's the generated proposal." Scroll a COVERED section — point to the
> `[DOC-xxx]` citation. "Every response cites the internal document it was
> grounded in."

Scroll to a red GAP row:
> "This one's flagged ACTION REQUIRED — no evidence on file. The agent tells the
> bid team exactly what to provide instead of bluffing."

Scroll to the **Bid Decision Report** appendix:
> "And it shows its full reasoning trace per requirement — evidence considered,
> score, citation-verification outcome, action required."

## [4:30–5:00] Close (be precise, don't overclaim)

> "Coverage score here is a requirement-coverage metric, not a win prediction —
> we're deliberate about that. The verifier guarantees citation *provenance*:
> every citation points to a real retrieved document. Built on Microsoft Foundry
> and Foundry IQ, on a $0 free-tier setup. A human approves before anything ships."

---

## Q&A backup

| Question | Honest answer |
|---|---|
| "Does it work on any RFP?" | It parses any PDF/DOCX; this is a proof of concept on a synthetic RFP + synthetic corpus. Real-world performance depends on how well the evidence corpus covers the RFP. |
| "How do you stop hallucination?" | The Verifier (no LLM) strips any citation that doesn't resolve to a retrieved document, and withholds sections with no valid citation. It verifies provenance; claim-level fact-checking is roadmap. |
| "Is it really Foundry?" | Yes — gpt-4.1 deployment for reasoning, Foundry IQ / Azure AI Search for retrieval. GitHub Models is a documented zero-cost fallback. |
| "Why so many gaps?" | The synthetic corpus only covers a fictional company's real capabilities; gaps are the system refusing to invent evidence — by design. |
| "Is the human approval gate removable?" | No, by design. The pipeline produces artifacts; a person decides before anything goes out. |
