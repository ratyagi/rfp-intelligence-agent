"""Tests for tools/dashboard.py — static HTML generation and escaping."""
import os

os.environ["STUB_MODE"] = "true"

from tools.dashboard import build_dashboard

VERIFIED_DRAFT = {
    "rfp_title": "GOV Cloud RFP",
    "company_name": "Contoso Cloud Solutions",
    "submission_date": "30 June 2026",
    "executive_summary": "We respond with verified evidence.",
    "coverage_score": 64,
    "gap_count": 1,
    "requirements": [
        {
            "id": "REQ-001", "text": "Migrate 500 VMs to Azure", "priority": "high",
            "category": "technical", "confidence": 0.9, "score": "COVERED",
            "response_text": "We migrated 620 VMs [DOC-001].",
            "verification": {"verified": ["DOC-001"], "stripped": []},
        },
        {
            "id": "REQ-002", "text": "Quantum-safe crypto plan", "priority": "high",
            "category": "technical", "confidence": 0.2, "score": "GAP",
            "response_text": None, "gap_note": "No evidence on file.",
            "verification": {"verified": [], "stripped": []},
        },
    ],
    "verification": {"citations_total": 1, "citations_verified": 1, "citations_stripped": 0},
}

REPORT = {
    "rfp_title": "GOV Cloud RFP", "coverage_score": 64,
    "recommendation": "BID WITH CONDITIONS", "recommendation_rationale": "Close the gaps.",
    "counts": {"total": 2, "covered": 1, "partial": 0, "gap": 1},
    "citations": {"total": 1, "verified": 1, "stripped": 0},
    "requirements": [],
}


def test_build_dashboard_writes_valid_html(tmp_path):
    out = build_dashboard(VERIFIED_DRAFT, REPORT, str(tmp_path / "dash.html"))
    html = open(out, encoding="utf-8").read()
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    assert "64%" in html
    assert "BID WITH CONDITIONS" in html
    assert "1/1" in html  # citations verified
    assert "REQ-001" in html and "REQ-002" in html
    assert "ACTION REQUIRED" in html  # the GAP row
    assert html.count('class="stage ') == 6  # six pipeline stages


def test_dashboard_escapes_model_text(tmp_path):
    """Model-generated text must be HTML-escaped (no injection / markup breakage)."""
    malicious = dict(VERIFIED_DRAFT)
    malicious["requirements"] = [{
        "id": "REQ-001", "text": "<script>alert('x')</script> & <b>bold</b>",
        "priority": "high", "category": "technical", "confidence": 0.9,
        "score": "COVERED", "response_text": "Response with <img src=x onerror=alert(1)>",
        "verification": {"verified": ["DOC-001"], "stripped": []},
    }]
    out = build_dashboard(malicious, REPORT, str(tmp_path / "dash.html"))
    html = open(out, encoding="utf-8").read()
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    assert "<img src=x onerror" not in html


def test_dashboard_handles_zero_citations(tmp_path):
    draft = dict(VERIFIED_DRAFT)
    draft["verification"] = {"citations_total": 0, "citations_verified": 0, "citations_stripped": 0}
    report = dict(REPORT, citations={"total": 0, "verified": 0, "stripped": 0})
    out = build_dashboard(draft, report, str(tmp_path / "dash.html"))
    assert "0/0" in open(out, encoding="utf-8").read()
