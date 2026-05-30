"""Teams Adaptive Card builder for the RFP review/approval workflow."""
import json


def build_approval_card(data: dict) -> dict:
    """Build a Teams Adaptive Card v1.5 payload for human review and approval.

    Args:
        data: dict with keys:
            rfp_title (str), submission_deadline (str|None), win_probability (int),
            gap_count (int), requirements_found (int), covered_count (int),
            partial_count (int), sharepoint_url (str), approve_webhook_url (str)

    Returns:
        Valid Adaptive Card JSON payload dict (schema v1.5).
    """
    rfp_title = data.get("rfp_title", "Untitled RFP")
    deadline = data.get("submission_deadline", "Not specified")
    win_prob = data.get("win_probability", 0)
    gap_count = data.get("gap_count", 0)
    reqs_found = data.get("requirements_found", 0)
    covered = data.get("covered_count", 0)
    partial = data.get("partial_count", 0)
    sharepoint_url = data.get("sharepoint_url", "https://sharepoint.example.com")
    approve_webhook = data.get("approve_webhook_url", "https://webhook.example.com/approve")

    win_color = "Good" if win_prob >= 70 else ("Warning" if win_prob >= 50 else "Attention")

    body = [
        {
            "type": "TextBlock",
            "text": "RFP Draft Ready for Review",
            "weight": "Bolder",
            "size": "Large",
            "color": "Accent",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": rfp_title,
            "weight": "Bolder",
            "size": "Medium",
            "wrap": True,
        },
        {
            "type": "ColumnSet",
            "columns": [
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [{
                        "type": "TextBlock",
                        "text": f"Submission deadline: **{deadline}**",
                        "wrap": True,
                        "size": "Small",
                    }]
                },
                {
                    "type": "Column",
                    "width": "auto",
                    "items": [{
                        "type": "TextBlock",
                        "text": f"Fit score: **{win_prob}%**",
                        "color": win_color,
                        "weight": "Bolder",
                        "size": "Medium",
                    }]
                },
            ]
        },
        {
            "type": "FactSet",
            "facts": [
                {"title": "Requirements found", "value": str(reqs_found)},
                {"title": "Covered", "value": str(covered)},
                {"title": "Partial", "value": str(partial)},
                {"title": "Gaps", "value": str(gap_count)},
                {"title": "Win probability", "value": f"{win_prob}%"},
            ]
        },
    ]

    if gap_count > 0:
        body.append({
            "type": "TextBlock",
            "text": f"⚠️ {gap_count} gap(s) require your input before submission",
            "color": "Attention",
            "weight": "Bolder",
            "wrap": True,
        })

    actions = [
        {
            "type": "Action.OpenUrl",
            "title": "View Draft",
            "url": sharepoint_url,
        },
        {
            "type": "Action.Http",
            "title": "Approve & Send to SharePoint",
            "method": "POST",
            "url": approve_webhook,
            "headers": [{"name": "Content-Type", "value": "application/json"}],
            "body": json.dumps({"action": "approve", "rfp_title": rfp_title}),
        },
        {
            "type": "Action.OpenUrl",
            "title": "Request Changes",
            "url": data.get(
                "teams_thread_url",
                "https://teams.microsoft.com/l/channel/placeholder"
            ),
        },
    ]

    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
        "actions": actions,
    }

    return card
