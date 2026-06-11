"""Agent 6: Review Agent — packages outputs for human review.

Produces the human-in-the-loop approval Adaptive Card as a rendered JSON
artifact alongside the proposal DOCX. Posting the card into a live Teams
channel (and routing the approval back) is deployment roadmap — see
docs/ARCHITECTURE.md. The approval gate itself is a design feature: nothing
in this pipeline sends a proposal anywhere without a human decision.
"""
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from tools.adaptive_card import build_approval_card

load_dotenv()
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))


def run(docx_path: str, scored_manifest: dict, meta: dict | None = None) -> dict:
    """Build the approval card artifact for the generated draft.

    Returns:
        {"card_path": str, "status": "pending_human_review"}
    """
    if meta is None:
        meta = {}

    scored_reqs = scored_manifest.get("scored_requirements", [])
    card = build_approval_card({
        "rfp_title": meta.get("rfp_title", "RFP Response"),
        "submission_deadline": meta.get("submission_deadline", "Not specified"),
        "win_probability": scored_manifest.get("win_probability", 0),
        "gap_count": scored_manifest.get("gap_count", 0),
        "requirements_found": len(scored_reqs),
        "covered_count": sum(1 for r in scored_reqs if r.get("score") == "COVERED"),
        "partial_count": sum(1 for r in scored_reqs if r.get("score") == "PARTIAL"),
        "docx_path": docx_path,
    })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    card_path = OUTPUT_DIR / (Path(docx_path).stem + "_approval_card.json")
    card_path.write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"ReviewAgent: approval card written to {card_path}")

    return {"card_path": str(card_path), "status": "pending_human_review"}
