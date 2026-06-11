"""Stage 6: Review — builds the verified proposal DOCX and the approval card.

Only verified content reaches this stage: the Verifier has already resolved
every citation and downgraded anything it couldn't ground. The approval
Adaptive Card is rendered as a local JSON artifact; posting it into a live
Teams channel is deployment roadmap (docs/ARCHITECTURE.md). The human
approval gate is a design feature: nothing in this pipeline sends a proposal
anywhere without a human decision.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from tools.adaptive_card import build_approval_card
from tools.docx_builder import build_proposal

load_dotenv()
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))
TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "proposal_template.docx"


def run(verified_draft: dict, meta: dict | None = None) -> dict:
    """Produce the proposal DOCX and approval card from the verified draft.

    Returns:
        {"docx_path": str, "card_path": str, "status": "pending_human_review"}
    """
    if meta is None:
        meta = {}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    docx_path = build_proposal(
        verified_draft,
        str(TEMPLATE_PATH),
        str(OUTPUT_DIR / f"draft_proposal_{timestamp}.docx"),
    )
    logger.info(f"ReviewAgent: DOCX written to {docx_path}")

    requirements = verified_draft.get("requirements", [])
    verification = verified_draft.get("verification", {})
    card = build_approval_card({
        "rfp_title": verified_draft.get("rfp_title", "RFP Response"),
        "submission_deadline": meta.get("submission_deadline", "Not specified"),
        "win_probability": verified_draft.get("win_probability", 0),
        "gap_count": verified_draft.get("gap_count", 0),
        "requirements_found": len(requirements),
        "covered_count": sum(1 for r in requirements if r.get("score") == "COVERED"),
        "partial_count": sum(1 for r in requirements if r.get("score") == "PARTIAL"),
        "citations_verified": (
            f"{verification.get('citations_verified', 0)}"
            f"/{verification.get('citations_total', 0)}"
        ),
        "docx_path": docx_path,
    })

    card_path = OUTPUT_DIR / f"draft_proposal_{timestamp}_approval_card.json"
    card_path.write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"ReviewAgent: approval card written to {card_path}")

    return {
        "docx_path": docx_path,
        "card_path": str(card_path),
        "status": "pending_human_review",
    }
