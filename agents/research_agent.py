"""Agent 2: Research Agent — searches M365 for evidence matching each requirement."""
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from tools.graph_client import GraphClient

load_dotenv()
logger = logging.getLogger(__name__)

STUB_MODE = lambda: os.getenv("STUB_MODE", "false").lower() == "true"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Which M365 sources to search per requirement category
CATEGORY_SOURCES = {
    "technical": ["sharepoint", "teams"],
    "commercial": ["sharepoint", "teams", "mail"],
    "legal": ["sharepoint"],
    "timeline": ["sharepoint", "mail"],
    "team": ["sharepoint", "teams"],
    "references": ["sharepoint"],
    "other": ["sharepoint", "teams", "mail"],
}


def run(manifest: dict) -> dict:
    """Build an evidence map for all requirements.

    Args:
        manifest: output of intake_agent.run() — {"requirements": [...]}

    Returns:
        {"REQ-001": [{"source", "title", "excerpt", "url", "relevance_note"}], ...}
    """
    requirements = manifest.get("requirements", [])
    site_id = os.getenv("SHAREPOINT_SITE_ID", "")
    gc = GraphClient()
    evidence_map = {}

    for req in requirements:
        req_id = req["id"]
        logger.info(f"ResearchAgent: searching evidence for {req_id}")
        sources = CATEGORY_SOURCES.get(req["category"], ["sharepoint"])
        candidates = _gather_candidates(gc, req["text"], sources, site_id)

        if STUB_MODE():
            evidence_map[req_id] = _annotate_stub(req, candidates)
        else:
            evidence_map[req_id] = _annotate_with_foundry(req, candidates)

    return evidence_map


def _gather_candidates(gc: GraphClient, query: str, sources: list, site_id: str) -> list:
    candidates = []
    if "sharepoint" in sources:
        for item in gc.search_sharepoint(query, site_id, top=3):
            candidates.append({"source": "SharePoint", **item})
    if "teams" in sources:
        for item in gc.search_teams(query, top=2):
            # normalise teams result shape to common fields
            candidates.append({
                "source": "Teams",
                "title": f"Teams: {item['channel']}",
                "excerpt": item["message"],
                "url": item["url"],
            })
    if "mail" in sources:
        for item in gc.search_mail(query, top=2):
            candidates.append({
                "source": "Mail",
                "title": item["subject"],
                "excerpt": item["excerpt"],
                "url": "",
            })
    return candidates


def _annotate_stub(req: dict, candidates: list) -> list:
    """Add hardcoded relevance notes in STUB mode — max 3 items.

    Timeline/admin requirements return no evidence (no internal doc covers submission deadlines).
    """
    if req.get("category") == "timeline":
        return []
    stub_notes = [
        "Directly evidences the required capability with comparable project scale and outcome metrics.",
        "Provides supporting documentation of compliance or certification relevant to this requirement.",
        "Confirms prior client agreement on the commercial or governance terms specified.",
    ]
    result = []
    for i, candidate in enumerate(candidates[:3]):
        result.append({
            **candidate,
            "relevance_note": stub_notes[i % len(stub_notes)],
        })
    return result


def _annotate_with_foundry(req: dict, candidates: list) -> list:
    """Call Foundry model to rank and annotate candidates with relevance notes."""
    if not candidates:
        return []

    system_prompt = (PROMPTS_DIR / "research_system.md").read_text(encoding="utf-8")
    user_message = json.dumps({
        "requirement": {
            "id": req["id"],
            "text": req["text"],
            "category": req["category"],
        },
        "evidence_candidates": candidates,
    }, ensure_ascii=False)

    endpoint = os.getenv("AZURE_FOUNDRY_ENDPOINT")
    api_key = os.getenv("AZURE_FOUNDRY_API_KEY")
    deployment = os.getenv("FOUNDRY_MODEL_DEPLOYMENT", "gpt-4o")

    if not endpoint or not api_key:
        raise EnvironmentError("AZURE_FOUNDRY_ENDPOINT and AZURE_FOUNDRY_API_KEY must be set in .env")

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
        max_tokens=1000,
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()
    try:
        annotated = json.loads(raw)
        return annotated.get("evidence", [])[:3]
    except json.JSONDecodeError:
        logger.error(f"ResearchAgent: failed to parse model output for {req['id']}")
        return candidates[:3]
