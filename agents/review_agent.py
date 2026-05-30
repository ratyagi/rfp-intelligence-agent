"""Agent 5: Review Agent — uploads DOCX to SharePoint, posts Teams Adaptive Card, handles approval."""
import json
import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from tools.adaptive_card import build_approval_card

load_dotenv()
logger = logging.getLogger(__name__)

STUB_MODE = lambda: os.getenv("STUB_MODE", "false").lower() == "true"
POLL_INTERVAL_SECONDS = 30
MAX_POLL_RETRIES = 10


def run(docx_path: str, scored_manifest: dict, meta: dict | None = None) -> dict:
    """Upload DOCX, post Teams card, and await human approval.

    Args:
        docx_path: path to the generated DOCX file
        scored_manifest: output of scorer_agent.run()
        meta: dict with rfp_title, company_name, submission_deadline

    Returns:
        {"sharepoint_url", "card_posted", "status", "final_file_url"}
    """
    if meta is None:
        meta = {}

    rfp_title = meta.get("rfp_title", "RFP Response")
    filename = f"DRAFT_{Path(docx_path).name}"
    site_id = os.getenv("SHAREPOINT_SITE_ID", "")
    output_folder = os.getenv("SHAREPOINT_OUTPUT_FOLDER", "/RFP-Outputs")

    sharepoint_url = _upload_to_sharepoint(docx_path, filename, site_id, output_folder)
    logger.info(f"ReviewAgent: DOCX upload target: {sharepoint_url}")

    gap_count = scored_manifest.get("gap_count", 0)
    scored_reqs = scored_manifest.get("scored_requirements", [])
    covered = sum(1 for r in scored_reqs if r.get("score") == "COVERED")
    partial = sum(1 for r in scored_reqs if r.get("score") == "PARTIAL")

    card_data = {
        "rfp_title": rfp_title,
        "submission_deadline": meta.get("submission_deadline", "Not specified"),
        "win_probability": scored_manifest.get("win_probability", 0),
        "gap_count": gap_count,
        "requirements_found": len(scored_reqs),
        "covered_count": covered,
        "partial_count": partial,
        "sharepoint_url": sharepoint_url,
        "approve_webhook_url": os.getenv("TEAMS_WEBHOOK_URL", "https://webhook.example.com/approve"),
        "teams_thread_url": f"https://teams.microsoft.com/l/channel/{os.getenv('TEAMS_CHANNEL_ID', 'placeholder')}",
    }

    card = build_approval_card(card_data)
    card_posted = _post_teams_card(card)

    if not card_posted:
        logger.warning("ReviewAgent: Teams card post failed — returning SharePoint URL as fallback")

    return {
        "sharepoint_url": sharepoint_url,
        "card_posted": card_posted,
        "status": "pending",
        "final_file_url": None,
    }


def _upload_to_sharepoint(docx_path: str, filename: str, site_id: str, folder: str) -> str:
    if STUB_MODE():
        # STUB: log the upload URL without making live API calls
        # TODO: replace with live Graph API PUT call when credentials are available
        upload_url = f"https://sharepoint.example.com/sites/{site_id}/drive/root:{folder}/{filename}:/content"
        logger.info(f"ReviewAgent [STUB]: would upload {docx_path} → {upload_url}")
        return f"https://sharepoint.example.com/sites/{site_id}/drive/root:{folder}/{filename}"

    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")

    if not all([tenant_id, client_id, client_secret, site_id]):
        raise EnvironmentError("Graph API credentials and SHAREPOINT_SITE_ID must be set in .env")

    try:
        from azure.identity import ClientSecretCredential
        credential = ClientSecretCredential(tenant_id, client_id, client_secret)
        token = credential.get_token("https://graph.microsoft.com/.default").token
    except Exception as e:
        raise RuntimeError(f"Failed to get Graph API token: {e}") from e

    upload_url = (
        f"https://graph.microsoft.com/v1.0/sites/{site_id}"
        f"/drive/root:{folder}/{filename}:/content"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    with open(docx_path, "rb") as f:
        response = requests.put(upload_url, headers=headers, data=f, timeout=60)

    if response.status_code not in (200, 201):
        raise RuntimeError(f"SharePoint upload failed: {response.status_code} {response.text}")

    return response.json().get("webUrl", upload_url)


def _post_teams_card(card: dict) -> bool:
    webhook_url = os.getenv("TEAMS_WEBHOOK_URL", "")

    if STUB_MODE():
        # STUB: log the card JSON without posting
        # TODO: replace with live webhook POST when TEAMS_WEBHOOK_URL is configured
        logger.info(f"ReviewAgent [STUB]: would POST Adaptive Card to Teams:\n{json.dumps(card, indent=2)}")
        return True

    if not webhook_url:
        logger.warning("ReviewAgent: TEAMS_WEBHOOK_URL not set — cannot post card")
        return False

    payload = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "contentUrl": None,
            "content": card,
        }]
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=30)
        if response.status_code == 200:
            logger.info("ReviewAgent: Adaptive Card posted to Teams successfully")
            return True
        else:
            logger.error(f"ReviewAgent: Teams POST failed: {response.status_code} {response.text}")
            return False
    except requests.RequestException as e:
        logger.error(f"ReviewAgent: Teams POST exception: {e}")
        return False


def poll_for_approval(approval_endpoint: str) -> str:
    """Poll an approval endpoint until a decision is received or timeout.

    Returns: "approved", "changes_requested", or "timed_out"
    """
    if STUB_MODE():
        logger.info("ReviewAgent [STUB]: skipping approval polling")
        return "pending"

    for attempt in range(MAX_POLL_RETRIES):
        try:
            response = requests.get(approval_endpoint, timeout=15)
            if response.status_code == 200:
                data = response.json()
                decision = data.get("decision")
                if decision in ("approved", "changes_requested"):
                    logger.info(f"ReviewAgent: approval decision received: {decision}")
                    return decision
        except requests.RequestException as e:
            logger.warning(f"ReviewAgent: poll attempt {attempt + 1} failed: {e}")

        logger.info(f"ReviewAgent: polling attempt {attempt + 1}/{MAX_POLL_RETRIES} — no decision yet")
        time.sleep(POLL_INTERVAL_SECONDS)

    logger.warning("ReviewAgent: timed out waiting for approval decision")
    return "timed_out"
