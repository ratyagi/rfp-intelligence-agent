"""Agent 3: Scorer Agent — scores each requirement COVERED/PARTIAL/GAP."""
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

STUB_MODE = lambda: os.getenv("STUB_MODE", "false").lower() == "true"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def run(manifest: dict, evidence_map: dict) -> dict:
    """Score requirements against the evidence map.

    Args:
        manifest: output of intake_agent.run()
        evidence_map: output of research_agent.run()

    Returns:
        {
            "scored_requirements": [{"id", "score", "confidence", "gap_note"}],
            "win_probability": int,
            "gap_count": int,
            "gaps_requiring_action": [{"id", "gap_note"}]
        }
    """
    requirements = manifest.get("requirements", [])

    if STUB_MODE():
        logger.info("ScorerAgent: running in STUB mode")
        return _stub_score(requirements, evidence_map)

    return _score_with_foundry(requirements, evidence_map)


def _stub_score(requirements: list, evidence_map: dict) -> dict:
    """Deterministic stub scoring: score based on evidence count in the map."""
    scored = []
    for req in requirements:
        req_id = req["id"]
        evidence = evidence_map.get(req_id, [])
        count = len(evidence)

        if count >= 2:
            score = "COVERED"
            confidence = 0.9
            gap_note = None
        elif count == 1:
            score = "PARTIAL"
            confidence = 0.55
            gap_note = (
                f"Provide additional documentation to fully substantiate the "
                f"'{req['category']}' requirement: {req['text'][:80]}..."
            )
        else:
            score = "GAP"
            confidence = 0.1
            gap_note = (
                f"Provide a case study or document demonstrating capability for: "
                f"{req['text'][:100]}..."
            )

        scored.append({
            "id": req_id,
            "score": score,
            "confidence": confidence,
            "gap_note": gap_note,
        })

    covered = sum(1 for s in scored if s["score"] == "COVERED")
    partial = sum(1 for s in scored if s["score"] == "PARTIAL")
    total = len(scored)
    win_probability = round((covered * 1.0 + partial * 0.5) / total * 100) if total > 0 else 0
    gap_count = sum(1 for s in scored if s["score"] == "GAP")
    gaps_requiring_action = [
        {"id": s["id"], "gap_note": s["gap_note"]}
        for s in scored if s["score"] in ("GAP", "PARTIAL") and s["gap_note"]
    ]

    logger.info(
        f"ScorerAgent: {covered} COVERED, {partial} PARTIAL, {gap_count} GAP "
        f"— win probability {win_probability}%"
    )

    return {
        "scored_requirements": scored,
        "win_probability": win_probability,
        "gap_count": gap_count,
        "gaps_requiring_action": gaps_requiring_action,
    }


def _score_with_foundry(requirements: list, evidence_map: dict) -> dict:
    system_prompt = (PROMPTS_DIR / "scorer_system.md").read_text(encoding="utf-8")
    user_message = json.dumps({
        "requirements": requirements,
        "evidence_map": evidence_map,
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
        max_tokens=4000,
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()
    try:
        result = json.loads(raw)
        logger.info(f"ScorerAgent: win probability {result.get('win_probability')}%")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"ScorerAgent: failed to parse model output as JSON: {e}")
        return {
            "scored_requirements": [],
            "win_probability": 0,
            "gap_count": 0,
            "gaps_requiring_action": [],
            "error": "Model returned invalid JSON",
        }
