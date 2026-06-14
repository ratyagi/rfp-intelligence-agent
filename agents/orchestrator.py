"""Foundry orchestrator — runs the six pipeline stages sequentially and returns a final status dict."""
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from tools.contracts import (
    DraftedProposal,
    EvidenceMap,
    RequirementManifest,
    ScoredManifest,
    VerifiedProposal,
)

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("orchestrator")

AGENT_TIMEOUT_SECONDS = 60
PIPELINE_TIMEOUT_SECONDS = 300


def run_pipeline(input: dict) -> dict:
    """Run the full six-stage RFP pipeline.

    Args:
        input: {
            "rfp_source": "file_path|sharepoint_url",
            "company_name": str,
            "rfp_title": str,
            "submission_deadline": str (optional)
        }

    Returns:
        {
            "status": "complete|partial|failed",
            "docx_path": str|None,
            "win_probability": int|None,
            "gap_count": int,
            "card_path": str|None
        }
    """
    pipeline_start = time.time()
    rfp_source = input.get("rfp_source", "")
    company_name = input.get("company_name", "Your Company")
    rfp_title = input.get("rfp_title", "RFP Response")
    submission_deadline = input.get("submission_deadline", "")

    meta = {
        "company_name": company_name,
        "rfp_title": rfp_title,
        "submission_deadline": submission_deadline,
    }

    result = {
        "status": "failed",
        "docx_path": None,
        "win_probability": None,
        "gap_count": 0,
        "card_path": None,
        "report_path": None,
        "errors": [],
    }

    # ── STAGE 1: INTAKE ──────────────────────────────────────────────────────
    parsed_doc = _run_agent("Stage1:Parse", _agent1_intake, result, rfp_source)
    if parsed_doc is None:
        result["status"] = "failed"
        return result

    # ── STAGE 2: RESEARCH ────────────────────────────────────────────────────
    from agents.intake_agent import run as intake_run
    manifest = _run_agent("Stage1:Extract", intake_run, result, parsed_doc)
    manifest = _validate_contract("Stage1:Extract", RequirementManifest, manifest, result)
    if manifest is None:
        result["status"] = "failed"
        return result

    from agents.research_agent import run as research_run
    evidence_map = _run_agent("Stage2:Research", research_run, result, manifest)
    evidence_map = _validate_contract("Stage2:Research", EvidenceMap, evidence_map, result)
    if evidence_map is None:
        result["status"] = "partial"
        evidence_map = {}

    # ── STAGE 3: SCORER ──────────────────────────────────────────────────────
    from agents.scorer_agent import run as scorer_run
    scored_manifest = _run_agent("Stage3:Scorer", scorer_run, result, manifest, evidence_map)
    scored_manifest = _validate_contract("Stage3:Scorer", ScoredManifest, scored_manifest, result)
    if scored_manifest is None:
        result["status"] = "partial"
        scored_manifest = {"scored_requirements": [], "win_probability": None, "gap_count": 0, "gaps_requiring_action": []}

    result["win_probability"] = scored_manifest.get("win_probability")
    result["gap_count"] = scored_manifest.get("gap_count", 0)

    # Enrich scored requirements with full requirement fields for the drafter.
    # The manifest is authoritative — contract validation fills these keys
    # with defaults, so overwrite rather than setdefault.
    req_lookup = {r["id"]: r for r in manifest.get("requirements", [])}
    for sr in scored_manifest.get("scored_requirements", []):
        orig = req_lookup.get(sr["id"], {})
        sr["text"] = orig.get("text") or sr.get("text", "")
        sr["priority"] = orig.get("priority") or sr.get("priority", "medium")
        sr["category"] = orig.get("category") or sr.get("category", "other")

    # ── STAGE 4: DRAFTER ─────────────────────────────────────────────────────
    from agents.drafter_agent import run as drafter_run
    draft = _run_agent("Stage4:Drafter", drafter_run, result, scored_manifest, evidence_map, meta)
    draft = _validate_contract("Stage4:Drafter", DraftedProposal, draft, result)

    # ── STAGE 5: VERIFIER ────────────────────────────────────────────────────
    verified_draft = None
    if draft is not None:
        from agents.verifier import run as verifier_run
        verified_draft = _run_agent("Stage5:Verifier", verifier_run, result, draft, evidence_map)
        verified_draft = _validate_contract("Stage5:Verifier", VerifiedProposal, verified_draft, result)
        if verified_draft is not None:
            # Post-verification numbers supersede the Scorer's.
            result["win_probability"] = verified_draft.get("win_probability")
            result["gap_count"] = verified_draft.get("gap_count", result["gap_count"])

    # ── STAGE 6: REVIEW ──────────────────────────────────────────────────────
    # Unverified drafts do not ship — Review only runs on Verifier output.
    if verified_draft is not None:
        from agents.review_agent import run as review_run
        review_result = _run_agent("Stage6:Review", review_run, result, verified_draft, evidence_map, meta)
        if review_result:
            result["docx_path"] = review_result.get("docx_path")
            result["card_path"] = review_result.get("card_path")
            result["report_path"] = review_result.get("report_path")
    else:
        logger.warning("orchestrator: skipping Review — no verified draft available")

    elapsed = time.time() - pipeline_start
    if not result["errors"] and result["docx_path"]:
        result["status"] = "complete"
    elif result["docx_path"]:
        result["status"] = "partial"

    logger.info(
        f"orchestrator: pipeline done in {elapsed:.1f}s — "
        f"status={result['status']}, win_prob={result['win_probability']}%, "
        f"gaps={result['gap_count']}"
    )
    return result


def _agent1_intake(rfp_source: str) -> dict:
    from tools.doc_intelligence import parse_rfp
    if rfp_source.startswith("http"):
        raise ValueError(
            "URL sources are not supported — download the RFP and pass a local "
            ".pdf or .docx path (remote sources are deployment roadmap)"
        )
    return parse_rfp(rfp_source)


def _validate_contract(name: str, contract, data, result: dict):
    """Validate a stage's output against its inter-stage Pydantic contract.

    Returns the normalised (model_dump) payload, or None — recorded as a
    stage error — if the payload doesn't honour the contract. None input
    (stage already failed) passes through.
    """
    if data is None:
        return None
    try:
        return contract.model_validate(data).model_dump()
    except ValidationError as e:
        error_msg = (
            f"{name} output violated the {contract.__name__} contract: "
            f"{e.error_count()} validation error(s)"
        )
        logger.error(f"orchestrator: {error_msg}\n{e}")
        result["errors"].append(error_msg)
        return None


def _run_agent(name: str, fn, result: dict, *args) -> object | None:
    logger.info(f"orchestrator: starting {name}")
    start = time.time()
    try:
        output = fn(*args)
        elapsed = time.time() - start
        if elapsed > AGENT_TIMEOUT_SECONDS:
            logger.warning(f"orchestrator: {name} exceeded timeout ({elapsed:.1f}s)")
        else:
            logger.info(f"orchestrator: {name} completed in {elapsed:.1f}s")
        return output
    except Exception as e:
        elapsed = time.time() - start
        error_msg = f"{name} failed after {elapsed:.1f}s: {e}"
        logger.error(f"orchestrator: {error_msg}")
        result["errors"].append(error_msg)
        return None


if __name__ == "__main__":
    import json
    import sys

    rfp_path = sys.argv[1] if len(sys.argv) > 1 else "demo/sample_rfp.pdf"
    output = run_pipeline({
        "rfp_source": rfp_path,
        "company_name": "Contoso Cloud Solutions",
        "rfp_title": "GOV-2026-ICT-0042 Cloud Infrastructure Modernisation",
        "submission_deadline": "30 June 2026",
    })
    print(json.dumps(output, indent=2))
