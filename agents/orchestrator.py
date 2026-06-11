"""Foundry orchestrator — runs Agents 1–5 sequentially and returns a final status dict."""
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

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
    """Run the full five-agent RFP pipeline.

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
            "teams_card_posted": bool
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
        "teams_card_posted": False,
        "errors": [],
    }

    # ── AGENT 1: INTAKE ──────────────────────────────────────────────────────
    parsed_doc = _run_agent("Agent1:Intake", _agent1_intake, result, rfp_source)
    if parsed_doc is None:
        result["status"] = "failed"
        return result

    # ── AGENT 2: RESEARCH ────────────────────────────────────────────────────
    from agents.intake_agent import run as intake_run
    manifest = _run_agent("Agent2a:IntakeExtract", intake_run, result, parsed_doc)
    if manifest is None:
        result["status"] = "failed"
        return result

    from agents.research_agent import run as research_run
    evidence_map = _run_agent("Agent2b:Research", research_run, result, manifest)
    if evidence_map is None:
        result["status"] = "partial"
        evidence_map = {}

    # ── AGENT 3: SCORER ──────────────────────────────────────────────────────
    from agents.scorer_agent import run as scorer_run
    scored_manifest = _run_agent("Agent3:Scorer", scorer_run, result, manifest, evidence_map)
    if scored_manifest is None:
        result["status"] = "partial"
        scored_manifest = {"scored_requirements": [], "win_probability": None, "gap_count": 0, "gaps_requiring_action": []}

    result["win_probability"] = scored_manifest.get("win_probability")
    result["gap_count"] = scored_manifest.get("gap_count", 0)

    # Enrich scored requirements with full requirement fields for the drafter
    req_lookup = {r["id"]: r for r in manifest.get("requirements", [])}
    for sr in scored_manifest.get("scored_requirements", []):
        orig = req_lookup.get(sr["id"], {})
        sr.setdefault("text", orig.get("text", ""))
        sr.setdefault("priority", orig.get("priority", "medium"))
        sr.setdefault("category", orig.get("category", "other"))

    # ── AGENT 4: DRAFTER ─────────────────────────────────────────────────────
    from agents.drafter_agent import run as drafter_run
    docx_path = _run_agent("Agent4:Drafter", drafter_run, result, scored_manifest, evidence_map, meta)
    if docx_path is None:
        result["status"] = "partial"
    else:
        result["docx_path"] = docx_path

    # ── AGENT 5: REVIEW ──────────────────────────────────────────────────────
    if docx_path:
        from agents.review_agent import run as review_run
        review_result = _run_agent("Agent5:Review", review_run, result, docx_path, scored_manifest, meta)
        if review_result:
            result["teams_card_posted"] = review_result.get("card_posted", False)
    else:
        logger.warning("orchestrator: skipping Agent 5 — no DOCX available")

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
        # STUB: SharePoint URL source not yet implemented
        # TODO: download file from SharePoint via Graph API before parsing
        logger.warning("orchestrator: SharePoint URL source not yet implemented — using STUB doc")
        from tools.doc_intelligence import _stub_result
        return _stub_result()
    return parse_rfp(rfp_source)


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
