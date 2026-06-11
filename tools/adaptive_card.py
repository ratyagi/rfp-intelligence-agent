"""Teams Adaptive Card builder for the RFP review/approval workflow."""


def build_approval_card(data: dict) -> dict:
    """Build a Teams Adaptive Card v1.5 payload for human review and approval.

    Args:
        data: dict with keys:
            rfp_title (str), submission_deadline (str|None), win_probability (int),
            gap_count (int), requirements_found (int), covered_count (int),
            partial_count (int), docx_path (str)

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
    docx_path = data.get("docx_path", "")

    win_color = "Good" if win_prob >= 70 else ("Warning" if win_prob >= 50 else "Attention")

    citations_verified = data.get("citations_verified", "")

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
                {"title": "Citations verified", "value": citations_verified or "n/a"},
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

    # Action.Submit payloads are consumed by whatever host renders the card
    # (Teams bot / Copilot) — routing them is deployment roadmap.
    actions = [
        {
            "type": "Action.Submit",
            "title": "View Draft",
            "data": {"action": "view_draft", "docx_path": docx_path},
        },
        {
            "type": "Action.Submit",
            "title": "Approve Draft",
            "data": {"action": "approve", "rfp_title": rfp_title},
        },
        {
            "type": "Action.Submit",
            "title": "Request Changes",
            "data": {"action": "request_changes", "rfp_title": rfp_title},
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
