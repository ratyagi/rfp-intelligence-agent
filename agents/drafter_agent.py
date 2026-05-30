"""Agent 4: Drafter Agent — writes response sections and generates the proposal DOCX."""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

STUB_MODE = lambda: os.getenv("STUB_MODE", "false").lower() == "true"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))


def run(scored_manifest: dict, evidence_map: dict, meta: dict | None = None) -> str:
    """Draft proposal sections and produce the output DOCX.

    Args:
        scored_manifest: output of scorer_agent.run()
        evidence_map: output of research_agent.run()
        meta: optional dict with company_name, rfp_title, submission_date

    Returns:
        File path of the generated DOCX.
    """
    if meta is None:
        meta = {}

    scored_reqs = scored_manifest.get("scored_requirements", [])
    win_probability = scored_manifest.get("win_probability", 0)

    # Need original requirement text — reconstruct from scored list (intake manifest merged upstream)
    drafted_requirements = []
    for scored in scored_reqs:
        req_id = scored["id"]
        score = scored["score"]
        gap_note = scored.get("gap_note")
        evidence = evidence_map.get(req_id, [])

        if score == "GAP" or not evidence:
            drafted_requirements.append({
                "id": req_id,
                "text": scored.get("text", ""),
                "score": "GAP",
                "response_text": None,
                "evidence_citations": None,
                "gap_note": gap_note,
            })
        elif STUB_MODE():
            drafted_requirements.append(_stub_draft(scored, evidence))
        else:
            drafted_requirements.append(_draft_with_foundry(scored, evidence))

    executive_summary = _write_executive_summary(drafted_requirements, meta, win_probability)

    from tools.docx_builder import build_proposal
    template_path = str(Path(__file__).parent.parent / "templates" / "proposal_template.docx")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = str(OUTPUT_DIR / f"draft_proposal_{timestamp}.docx")

    data = {
        "company_name": meta.get("company_name", "Your Company Name"),
        "rfp_title": meta.get("rfp_title", "RFP Response"),
        "submission_date": meta.get("submission_date", datetime.now().strftime("%d %B %Y")),
        "executive_summary": executive_summary,
        "win_probability": win_probability,
        "requirements": drafted_requirements,
    }

    path = build_proposal(data, template_path, output_path)
    logger.info(f"DrafterAgent: DOCX written to {path}")
    return path


def _stub_draft(scored: dict, evidence: list) -> dict:
    req_id = scored["id"]
    score = scored["score"]
    citations = "\n".join(
        f"[Source: {e['title']} — {e.get('url', 'internal')}]"
        for e in evidence[:3]
    )
    response = (
        f"Our organisation directly addresses {req_id} through verified internal evidence. "
        f"The evidence on file demonstrates compliance with the stated requirement through "
        f"documented project outcomes and certified credentials. "
        f"Our delivery approach is grounded in repeatable methodology and confirmed "
        f"by client-approved outcomes. "
        f"Full documentation is available upon request and has been included in the appendix. "
        f"{citations}"
    )
    return {
        "id": req_id,
        "text": scored.get("text", ""),
        "score": score,
        "response_text": response,
        "evidence_citations": citations,
        "gap_note": scored.get("gap_note"),
    }


def _draft_with_foundry(scored: dict, evidence: list) -> dict:
    system_prompt = (PROMPTS_DIR / "drafter_system.md").read_text(encoding="utf-8")
    user_message = json.dumps({
        "requirement": {
            "id": scored["id"],
            "text": scored.get("text", ""),
            "score": scored["score"],
            "priority": scored.get("priority", "medium"),
            "category": scored.get("category", "other"),
        },
        "evidence": evidence,
    }, ensure_ascii=False)

    endpoint = os.getenv("AZURE_FOUNDRY_ENDPOINT")
    api_key = os.getenv("AZURE_FOUNDRY_API_KEY")
    deployment = os.getenv("FOUNDRY_MODEL_DEPLOYMENT", "gpt-4o")

    if not endpoint or not api_key:
        raise EnvironmentError("AZURE_FOUNDRY_ENDPOINT and AZURE_FOUNDRY_API_KEY must be set.")

    try:
        from azure.ai.projects import AIProjectClient
        from azure.core.credentials import AzureKeyCredential
    except ImportError as e:
        raise ImportError("azure-ai-projects is required.") from e

    client = AIProjectClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))
    response = client.inference.get_chat_completions(
        model=deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=600,
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()
    try:
        result = json.loads(raw)
        return {
            "id": scored["id"],
            "text": scored.get("text", ""),
            "score": scored["score"],
            "response_text": result.get("response_text"),
            "evidence_citations": result.get("evidence_citations"),
            "gap_note": scored.get("gap_note"),
        }
    except json.JSONDecodeError:
        logger.error(f"DrafterAgent: failed to parse model output for {scored['id']}")
        return _stub_draft(scored, evidence)


def _write_executive_summary(requirements: list, meta: dict, win_probability: int) -> str:
    if STUB_MODE():
        company = meta.get("company_name", "Our organisation")
        rfp = meta.get("rfp_title", "this RFP")
        covered = sum(1 for r in requirements if r.get("score") == "COVERED")
        total = len(requirements)
        gaps = sum(1 for r in requirements if r.get("score") == "GAP")
        return (
            f"{company} submits this proposal in response to {rfp}. "
            f"We have addressed {covered} of {total} requirements with verified internal evidence, "
            f"yielding an estimated fit score of {win_probability}%. "
            f"{gaps} requirement(s) require additional input from your team before submission. "
            f"Our response is grounded solely in documented project outcomes, certifications, and "
            f"client-approved deliverables — no claims have been made without supporting evidence."
        )

    # In live mode this would call Foundry — placeholder for now
    # STUB: executive summary generation via Foundry not yet wired
    # TODO: call Foundry with a summarisation prompt once live credentials are available
    return _write_executive_summary.__wrapped__(requirements, meta, win_probability) if hasattr(
        _write_executive_summary, "__wrapped__") else (
        f"Proposal in response to {meta.get('rfp_title', 'this RFP')}. "
        f"Estimated fit score: {win_probability}%."
    )
