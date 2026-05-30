"""Agent 1: Intake Agent — extracts structured requirements from parsed RFP text."""
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

STUB_MODE = lambda: os.getenv("STUB_MODE", "false").lower() == "true"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


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
    user_message = json.dumps({
        "full_text": parsed_doc.get("full_text", ""),
        "sections": parsed_doc.get("sections", []),
    }, ensure_ascii=False)

    raw = _call_foundry(system_prompt, user_message)

    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"IntakeAgent: failed to parse model output as JSON: {e}")
        return {"requirements": [], "error": "Model returned invalid JSON"}

    if "requirements" not in manifest:
        return {"requirements": [], "error": "Model output missing 'requirements' key"}

    logger.info(f"IntakeAgent: extracted {len(manifest['requirements'])} requirements")
    return manifest


def _call_foundry(system_prompt: str, user_message: str) -> str:
    endpoint = os.getenv("AZURE_FOUNDRY_ENDPOINT")
    api_key = os.getenv("AZURE_FOUNDRY_API_KEY")
    deployment = os.getenv("FOUNDRY_MODEL_DEPLOYMENT", "gpt-4o")

    if not endpoint or not api_key:
        raise EnvironmentError(
            "AZURE_FOUNDRY_ENDPOINT and AZURE_FOUNDRY_API_KEY must be set in .env"
        )

    try:
        from azure.ai.projects import AIProjectClient
        from azure.core.credentials import AzureKeyCredential
    except ImportError as e:
        raise ImportError("azure-ai-projects is required. Run: pip install azure-ai-projects") from e

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
    return response.choices[0].message.content.strip()


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
