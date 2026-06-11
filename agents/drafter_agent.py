"""Agent 4: Drafter Agent — writes response sections and generates the proposal DOCX.

Drafted sections may cite only documents present in the evidence retrieved for
their requirement, using inline [DOC-xxx] markers. The Verifier (next stage)
resolves every marker against the evidence map and strips anything that
doesn't resolve.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from tools.foundry_client import chat, chat_json

load_dotenv()
logger = logging.getLogger(__name__)

STUB_MODE = lambda: os.getenv("STUB_MODE", "false").lower() == "true"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def run(scored_manifest: dict, evidence_map: dict, meta: dict | None = None) -> dict:
    """Draft proposal sections for every scored requirement.

    Returns:
        Draft data for the Verifier and Review stages:
        {company_name, rfp_title, submission_date, executive_summary,
         win_probability, requirements: [drafted requirement dicts]}
    """
    if meta is None:
        meta = {}

    scored_reqs = scored_manifest.get("scored_requirements", [])
    win_probability = scored_manifest.get("win_probability", 0)

    drafted_requirements = []
    for scored in scored_reqs:
        req_id = scored["id"]
        evidence = evidence_map.get(req_id, [])

        if scored["score"] == "GAP" or not evidence:
            drafted_requirements.append({
                "id": req_id,
                "text": scored.get("text", ""),
                "priority": scored.get("priority", "medium"),
                "score": "GAP",
                "response_text": None,
                "evidence_citations": None,
                "gap_note": scored.get("gap_note"),
            })
        elif STUB_MODE():
            drafted_requirements.append(_stub_draft(scored, evidence))
        else:
            drafted_requirements.append(_draft_one(scored, evidence))

    executive_summary = _write_executive_summary(drafted_requirements, meta, win_probability)
    logger.info(f"DrafterAgent: drafted {len(drafted_requirements)} sections")

    return {
        "company_name": meta.get("company_name", "Your Company Name"),
        "rfp_title": meta.get("rfp_title", "RFP Response"),
        "submission_date": meta.get("submission_date", datetime.now().strftime("%d %B %Y")),
        "executive_summary": executive_summary,
        "win_probability": win_probability,
        "requirements": drafted_requirements,
    }


def _draft_one(scored: dict, evidence: list) -> dict:
    system_prompt = (PROMPTS_DIR / "drafter_system.md").read_text(encoding="utf-8")
    result = chat_json(
        system_prompt,
        json.dumps({
            "requirement": {
                "id": scored["id"],
                "text": scored.get("text", ""),
                "score": scored["score"],
                "priority": scored.get("priority", "medium"),
                "category": scored.get("category", "other"),
            },
            "evidence": [
                {"doc_id": e["doc_id"], "title": e["title"], "excerpt": e["excerpt"]}
                for e in evidence
            ],
        }, ensure_ascii=False),
        max_tokens=450,
        temperature=0.2,
    )
    return {
        "id": scored["id"],
        "text": scored.get("text", ""),
        "priority": scored.get("priority", "medium"),
        "score": scored["score"],
        "response_text": result.get("response_text"),
        "evidence_citations": result.get("evidence_citations"),
        "gap_note": scored.get("gap_note"),
    }


def _stub_draft(scored: dict, evidence: list) -> dict:
    req_id = scored["id"]
    citations = "\n".join(
        f"[{e['doc_id']}: {e['title']} — {e.get('source_path', 'corpus')}]"
        for e in evidence[:3]
    )
    inline_ids = " ".join(f"[{e['doc_id']}]" for e in evidence[:3])
    response = (
        f"Our organisation directly addresses {req_id} through verified internal evidence "
        f"{inline_ids}. The evidence on file demonstrates compliance with the stated "
        f"requirement through documented project outcomes and certified credentials. "
        f"Our delivery approach is grounded in repeatable methodology and confirmed "
        f"by client-approved outcomes. "
        f"Full documentation is available upon request and has been included in the appendix."
    )
    return {
        "id": req_id,
        "text": scored.get("text", ""),
        "priority": scored.get("priority", "medium"),
        "score": scored["score"],
        "response_text": response,
        "evidence_citations": citations,
        "gap_note": scored.get("gap_note"),
    }


def _write_executive_summary(requirements: list, meta: dict, win_probability: int) -> str:
    company = meta.get("company_name", "Our organisation")
    rfp = meta.get("rfp_title", "this RFP")
    covered = sum(1 for r in requirements if r.get("score") == "COVERED")
    partial = sum(1 for r in requirements if r.get("score") == "PARTIAL")
    gaps = sum(1 for r in requirements if r.get("score") == "GAP")
    total = len(requirements)

    if STUB_MODE():
        return (
            f"{company} submits this proposal in response to {rfp}. "
            f"We have addressed {covered} of {total} requirements with verified internal evidence, "
            f"yielding an estimated fit score of {win_probability}%. "
            f"{gaps} requirement(s) require additional input from your team before submission. "
            f"Our response is grounded solely in documented project outcomes, certifications, and "
            f"client-approved deliverables — no claims have been made without supporting evidence."
        )

    return chat(
        "You write concise executive summaries for RFP response proposals. "
        "Write 4-6 sentences of plain professional prose. State only the facts "
        "provided — do not invent capabilities, clients, or numbers.",
        json.dumps({
            "company_name": company,
            "rfp_title": rfp,
            "requirements_total": total,
            "covered": covered,
            "partial": partial,
            "gaps": gaps,
            "win_probability_percent": win_probability,
            "note": (
                "The proposal is grounded in the company's verified internal "
                "evidence base; gaps are explicitly flagged for human input "
                "rather than papered over."
            ),
        }),
        max_tokens=300,
        temperature=0.3,
    )
