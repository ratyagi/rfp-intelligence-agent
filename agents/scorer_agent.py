"""Agent 3: Scorer Agent — scores each requirement COVERED/PARTIAL/GAP.

The model judges one requirement at a time (small calls — survives throttled
free-trial subscriptions). The win probability is never produced by the
model: it is deterministic, priority-weighted math computed in code.
"""
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from tools.foundry_client import chat_json

load_dotenv()
logger = logging.getLogger(__name__)

STUB_MODE = lambda: os.getenv("STUB_MODE", "false").lower() == "true"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

PRIORITY_WEIGHTS = {"high": 3, "medium": 2, "low": 1}
SCORE_CREDIT = {"COVERED": 1.0, "PARTIAL": 0.5, "GAP": 0.0}


def run(manifest: dict, evidence_map: dict) -> dict:
    """Score requirements against the evidence map.

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
        scored = [_stub_score_one(req, evidence_map.get(req["id"], [])) for req in requirements]
    else:
        scored = [_score_one(req, evidence_map.get(req["id"], [])) for req in requirements]

    return _aggregate(requirements, scored)


def _score_one(req: dict, evidence: list) -> dict:
    """LLM judgement for a single requirement against its retrieved evidence."""
    if not evidence:
        # No retrieval hits is a deterministic GAP — no model call needed.
        return {
            "id": req["id"],
            "score": "GAP",
            "confidence": 0.95,
            "gap_note": (
                f"No internal evidence found for this requirement. Provide "
                f"documentation covering: {req['text'][:120]}..."
            ),
        }

    system_prompt = (PROMPTS_DIR / "scorer_system.md").read_text(encoding="utf-8")
    result = chat_json(
        system_prompt,
        json.dumps({
            "requirement": {
                "id": req["id"],
                "text": req["text"],
                "priority": req.get("priority", "medium"),
                "category": req.get("category", "other"),
            },
            "evidence": [
                {"doc_id": e["doc_id"], "title": e["title"], "excerpt": e["excerpt"]}
                for e in evidence
            ],
        }, ensure_ascii=False),
        max_tokens=300,
    )

    score = result.get("score", "GAP")
    if score not in SCORE_CREDIT:
        logger.warning(f"ScorerAgent: invalid score '{score}' for {req['id']} — treating as GAP")
        score = "GAP"
    return {
        "id": req["id"],
        "score": score,
        "confidence": float(result.get("confidence", 0.5)),
        "gap_note": result.get("gap_note") if score in ("GAP", "PARTIAL") else None,
    }


def _stub_score_one(req: dict, evidence: list) -> dict:
    """Deterministic stub: score by evidence count."""
    count = len(evidence)
    if count >= 2:
        return {"id": req["id"], "score": "COVERED", "confidence": 0.9, "gap_note": None}
    if count == 1:
        return {
            "id": req["id"], "score": "PARTIAL", "confidence": 0.55,
            "gap_note": (
                f"Provide additional documentation to fully substantiate the "
                f"'{req.get('category', 'other')}' requirement: {req['text'][:80]}..."
            ),
        }
    return {
        "id": req["id"], "score": "GAP", "confidence": 0.1,
        "gap_note": (
            f"Provide a case study or document demonstrating capability for: "
            f"{req['text'][:100]}..."
        ),
    }


def _aggregate(requirements: list, scored: list) -> dict:
    """Deterministic roll-up: priority-weighted win probability and gap list.

    win_probability = Σ weight(req) × credit(score) / Σ weight(req)
    A gap on a high-priority requirement hurts three times as much as one on
    a low-priority requirement.
    """
    priority_by_id = {r["id"]: r.get("priority", "medium") for r in requirements}

    total_weight = 0
    earned = 0.0
    for s in scored:
        weight = PRIORITY_WEIGHTS.get(priority_by_id.get(s["id"], "medium"), 2)
        total_weight += weight
        earned += weight * SCORE_CREDIT[s["score"]]
    win_probability = round(earned / total_weight * 100) if total_weight else 0

    gap_count = sum(1 for s in scored if s["score"] == "GAP")
    covered = sum(1 for s in scored if s["score"] == "COVERED")
    partial = sum(1 for s in scored if s["score"] == "PARTIAL")
    gaps_requiring_action = [
        {"id": s["id"], "gap_note": s["gap_note"]}
        for s in scored if s["score"] in ("GAP", "PARTIAL") and s.get("gap_note")
    ]

    logger.info(
        f"ScorerAgent: {covered} COVERED, {partial} PARTIAL, {gap_count} GAP "
        f"— priority-weighted win probability {win_probability}%"
    )
    return {
        "scored_requirements": scored,
        "win_probability": win_probability,
        "gap_count": gap_count,
        "gaps_requiring_action": gaps_requiring_action,
    }
