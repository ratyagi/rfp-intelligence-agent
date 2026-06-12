"""Agent 1: Intake Agent — extracts structured requirements from parsed RFP text."""
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from pydantic import ValidationError

from tools.contracts import IntakeExtraction
from tools.foundry_client import chat_json, estimate_tokens

load_dotenv()
logger = logging.getLogger(__name__)

STUB_MODE = lambda: os.getenv("STUB_MODE", "false").lower() == "true"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Each extraction call stays small so the pipeline runs even on free-trial
# subscriptions throttled to ~1,000 tokens/minute.
MAX_CHUNK_TOKENS = 550


def run(parsed_doc: dict) -> dict:
    """Extract a requirement manifest from the parsed RFP document.

    Args:
        parsed_doc: output of tools.doc_intelligence.parse_rfp()

    Returns:
        {"requirements": [{"id", "text", "priority", "category"}]}
    """
    if STUB_MODE():
        logger.info("IntakeAgent: running in STUB mode")
        return _stub_manifest()

    system_prompt = (PROMPTS_DIR / "intake_system.md").read_text(encoding="utf-8")
    sections = parsed_doc.get("sections", [])
    if not sections:
        sections = [{"heading": "Document", "content": parsed_doc.get("full_text", "")}]

    requirements = []
    for chunk_index, chunk in enumerate(_chunk_sections(sections), start=1):
        logger.info(f"IntakeAgent: extracting from chunk {chunk_index} "
                    f"({len(chunk)} section(s))")
        try:
            result = chat_json(
                system_prompt,
                json.dumps({"sections": chunk}, ensure_ascii=False),
                max_tokens=900,
                schema=IntakeExtraction,
            )
        except ValidationError as e:
            # One chunk failing schema twice loses its requirements, not the run.
            logger.warning(f"IntakeAgent: chunk {chunk_index} failed schema validation twice "
                           f"({e.error_count()} error(s)) — skipping chunk")
            continue
        requirements.extend(result["requirements"])

    # Renumber sequentially — chunked calls each start from REQ-001, and the
    # rest of the pipeline keys everything on unique IDs.
    for i, req in enumerate(requirements, start=1):
        req["id"] = f"REQ-{i:03d}"
        req.setdefault("priority", "medium")
        req.setdefault("category", "other")

    logger.info(f"IntakeAgent: extracted {len(requirements)} requirements")
    return {"requirements": requirements}


def _chunk_sections(sections: list) -> list:
    """Group sections into chunks that fit the per-call token budget.

    A single oversized section is split on paragraph boundaries.
    """
    chunks = []
    current, current_tokens = [], 0
    for section in sections:
        for piece in _split_section(section):
            piece_tokens = estimate_tokens(piece["heading"] + piece["content"])
            if current and current_tokens + piece_tokens > MAX_CHUNK_TOKENS:
                chunks.append(current)
                current, current_tokens = [], 0
            current.append(piece)
            current_tokens += piece_tokens
    if current:
        chunks.append(current)
    return chunks


def _split_section(section: dict) -> list:
    heading = section.get("heading", "")
    content = section.get("content", "")
    if estimate_tokens(content) <= MAX_CHUNK_TOKENS:
        return [{"heading": heading, "content": content}]

    pieces, buffer = [], ""
    for paragraph in content.split("\n"):
        if buffer and estimate_tokens(buffer + paragraph) > MAX_CHUNK_TOKENS:
            pieces.append({"heading": heading, "content": buffer.strip()})
            buffer = ""
        buffer += paragraph + "\n"
    if buffer.strip():
        pieces.append({"heading": heading, "content": buffer.strip()})
    return pieces


def _stub_manifest() -> dict:
    return {
        "requirements": [
            {
                "id": "REQ-001",
                "text": (
                    "The vendor must demonstrate proven experience migrating Windows Server 2012/2016 "
                    "workloads to Azure IaaS and PaaS services, with a minimum of 3 completed migrations "
                    "of comparable scale (500+ VMs) evidenced by reference contacts."
                ),
                "priority": "high",
                "category": "technical",
            },
            {
                "id": "REQ-002",
                "text": (
                    "The solution must achieve 99.95% uptime SLA for Tier-1 production workloads with "
                    "monitoring tooling, incident response procedures, and mean time to recovery (MTTR) "
                    "under 30 minutes."
                ),
                "priority": "high",
                "category": "technical",
            },
            {
                "id": "REQ-003",
                "text": (
                    "All data must remain within Australian Azure data centre regions (Australia East, "
                    "Australia Southeast). The vendor must hold ISO 27001 certification and comply with "
                    "the Australian Government Information Security Manual (ISM)."
                ),
                "priority": "high",
                "category": "legal",
            },
            {
                "id": "REQ-004",
                "text": (
                    "The vendor must provide a zero-downtime migration plan using Azure Site Recovery or "
                    "equivalent. Cutover windows must not exceed 4 hours per workload group."
                ),
                "priority": "medium",
                "category": "technical",
            },
            {
                "id": "REQ-005",
                "text": (
                    "Pricing must be submitted as a fixed-price schedule for Years 1, 2, and 3 with a "
                    "capped annual escalation of CPI + 2%, inclusive of all licences, tooling, and "
                    "professional services."
                ),
                "priority": "high",
                "category": "commercial",
            },
            {
                "id": "REQ-006",
                "text": (
                    "A milestone-based payment schedule must be provided, with milestone completion "
                    "certified by DDT project director sign-off and net-30 payment terms."
                ),
                "priority": "medium",
                "category": "commercial",
            },
            {
                "id": "REQ-007",
                "text": (
                    "The proposed delivery team must include a named Project Manager with PMP or "
                    "PRINCE2 certification and a minimum of 7 years cloud migration experience. "
                    "Key personnel substitution requires DDT written approval."
                ),
                "priority": "high",
                "category": "team",
            },
            {
                "id": "REQ-008",
                "text": (
                    "The vendor must comply with the Privacy Act 1988 (Cth) and the Notifiable Data "
                    "Breaches scheme. Any data breach must be notified to DDT within 24 hours of discovery."
                ),
                "priority": "high",
                "category": "legal",
            },
            {
                "id": "REQ-009",
                "text": (
                    "Proposal submission deadline is 17:00 AEST on 30 June 2026 via the AusTender portal. "
                    "Late submissions will not be accepted."
                ),
                "priority": "low",
                "category": "timeline",
            },
        ]
    }
