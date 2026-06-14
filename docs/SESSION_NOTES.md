# Session handoff notes — Agents League hackathon

> Purpose: let any new Claude Code session continue this project with zero
> ramp-up. Read this file, then `docs/ARCHITECTURE.md` (the locked spec),
> then continue the task list below. Last updated: June 12, 2026.

## Project state

Six-stage RFP reasoning pipeline (Reasoning Agents track, Foundry IQ as the
mandatory Microsoft IQ layer). All work is on branch
`claude/happy-noether-wc43vl`, tracked by PR #1. 42/42 tests pass:

```bash
STUB_MODE=true RETRIEVAL_MODE=local python -m pytest tests/ -q
```

### Task list status (from the agreed plan)

| # | Task | Status |
|---|---|---|
| P0-1 | Lock architecture (Reasoning track + Foundry IQ) | ✅ done |
| P0-2 | Evidence corpus + 8-page sample RFP | ✅ done |
| P0-3 | Foundry IQ retrieval layer (local BM25 + knowledge-base client) | ✅ code done; live KB setup blocked on Azure creds |
| P0-4 | Shared rate-limit-aware model client, fixed live paths | ✅ done |
| P0-5 | First live end-to-end run + Pydantic validation | ✅ done (June 12) |
| P0-6 | Deterministic citation Verifier (stage 5) | ✅ done |
| P1-7 | Bid Decision Report (reasoning trace) | ✅ done |
| P1-8 | README rewrite | ⬜ not started |
| P1-9 | Demo script + video prep | ⬜ not started |
| P2-10 | Tests for real logic + repo hygiene | partially done along the way |

## P0-5 COMPLETED — first live run results (June 12)

Live end-to-end run on GitHub Models (`openai/gpt-4o-mini`,
`RETRIEVAL_MODE=local`, pypdf fallback for parsing since no DI creds):

- `status: complete` in 740s — 41 requirements extracted from the 8-page
  sample RFP, 10 COVERED / 8 PARTIAL / 23 GAP, requirement coverage score 33%,
  recommendation REVIEW BID DECISION.
- Verifier: 24/24 citations verified, 0 stripped. No JSON/schema retries
  were needed (gpt-4o-mini returned valid shapes throughout).
- Pydantic contracts shipped in `tools/contracts.py`; `chat_json(schema=...)`
  retries once on schema-invalid output; orchestrator validates every stage
  boundary. pypdf fallback added to `tools/doc_intelligence.py` (DI remains
  the documented path; warning logged).
- Note: many of the 23 GAPs are RFP boilerplate (definitions, submission
  instructions, conditions of tender) with legitimately no corpus coverage —
  honest-gaps narrative, but consider down-ranking boilerplate or adding
  corpus docs if a stronger demo number is wanted.
- Security review (June 12): no vulnerabilities in the diff; no secrets in
  git history. ACTION: user should rotate the GitHub PAT after the
  hackathon (it was pasted in chat / lives in ephemeral containers).
- Budget note: a full live run is ~50 calls vs the 150/day free tier —
  at most 1–2 more full runs per day.

## ARCHIVED: P0-5 task steps (done, kept for reference)

The user has no Azure OpenAI quota (free-trial subscription, refuses
pay-as-you-go — respect this). Model inference therefore uses the
**GitHub Models free tier** (`MODEL_PROVIDER=github_models`), already
supported in `tools/foundry_client.py`.

### Step 1 — recreate .env (SECRETS ARE NOT IN THE REPO)

Ask the user to paste their GitHub PAT (fine-grained, Models:read only).
Then write `.env` (gitignored):

```
MODEL_PROVIDER=github_models
GITHUB_MODELS_TOKEN=<paste from user>
GITHUB_MODELS_MODEL=openai/gpt-4o-mini
FOUNDRY_TPM_BUDGET=6000
RETRIEVAL_MODE=local
STUB_MODE=false
OUTPUT_DIR=./output
```

### Step 2 — verify network egress (the reason the last session restarted)

The previous container blocked `models.github.ai` (sandbox proxy 403:
"Host not in allowlist"). The user added allowed domains to the
environment; policies only apply to NEW containers. Verify with:

```bash
python -c "from tools.foundry_client import chat; print(chat('Test.','Reply with exactly: LIVE OK',max_tokens=10))"
```

- Success looks like: `LIVE OK`
- If it fails with "Host not in allowlist", the environment's allowed
  domains are still wrong — tell the user to check the environment's
  network settings include: `models.github.ai`,
  `models.inference.ai.azure.com`, `*.search.windows.net`,
  `*.cognitiveservices.azure.com`, `*.services.ai.azure.com`,
  `*.openai.azure.com`.

### Step 3 — first live pipeline run

`demo/sample_rfp.pdf` parsing: the user has no Document Intelligence
resource yet. `tools/doc_intelligence.py` live path requires DI creds —
if absent, ADD a local pypdf fallback (parse text + split sections on
numbered headings like `^\d+\. ` / `Appendix [A-Z]`), log a clear warning
that DI is the documented path. Then:

```bash
python -m agents.orchestrator demo/sample_rfp.pdf
```

Budget: GitHub Models free tier = 15 req/min, 150 req/day; a full run is
~25–30 calls. Expect ~5 minutes with pacing. Debug model-output issues
(JSON shape, citation format) as they surface.

### Step 4 — remaining P0-5 work

- Pydantic models for inter-stage contracts (RequirementManifest,
  EvidenceMap, ScoredManifest, DraftedProposal, VerifiedProposal) with
  one retry on schema-invalid model output (chat_json already retries
  parse errors; extend for schema errors).
- Commit and push everything to `claude/happy-noether-wc43vl`.

## Still waiting on the user (Azure side)

1. Azure AI Search resource (try Free tier; Basic from trial credit if
   semantic ranking needs it) → endpoint + admin key → then run
   `python scripts/setup_foundry_iq.py` and flip `RETRIEVAL_MODE=foundry_iq`.
2. Document Intelligence F0 (free) → endpoint + key.
3. Verdict on whether gpt-4o-mini can be deployed on their free trial
   (if yes, the recorded demo should use `MODEL_PROVIDER=foundry`).

## Hard constraints (do not violate)

- User pays $0 out of pocket; no pay-as-you-go upgrade.
- Never commit secrets (.env is gitignored; keys live only in chat + .env).
- Honesty over claims: no fake/stubbed demo surfaces presented as real.
- Hackathon deadline: **June 14, 2026**. Demo video + public repo required.
