"""Tests for the deterministic citation Verifier (stage 5)."""
from agents.verifier import run as verify


def _draft(requirements):
    return {
        "rfp_title": "Test RFP",
        "win_probability": 0,
        "requirements": requirements,
    }


EVIDENCE_MAP = {
    "REQ-001": [
        {"doc_id": "DOC-001", "title": "HealthGov Case Study", "excerpt": "...",
         "source_path": "corpus/DOC-001.md", "score": 15.0},
        {"doc_id": "DOC-002", "title": "StateGov Case Study", "excerpt": "...",
         "source_path": "corpus/DOC-002.md", "score": 12.0},
    ],
    "REQ-002": [
        {"doc_id": "DOC-010", "title": "Incident Response Runbook", "excerpt": "...",
         "source_path": "corpus/DOC-010.md", "score": 20.0},
    ],
    "REQ-003": [],
}


def test_valid_citations_pass_unchanged():
    draft = _draft([{
        "id": "REQ-001", "priority": "high", "score": "COVERED",
        "response_text": "We migrated 620 VMs [DOC-001] and 540 VMs [DOC-002].",
        "evidence_citations": "old", "gap_note": None,
    }])
    result = verify(draft, EVIDENCE_MAP)
    req = result["requirements"][0]
    assert req["score"] == "COVERED"
    assert "[DOC-001]" in req["response_text"] and "[DOC-002]" in req["response_text"]
    assert req["evidence_citations"] == "[DOC-001] HealthGov Case Study\n[DOC-002] StateGov Case Study"
    assert result["verification"]["citations_verified"] == 2
    assert result["verification"]["citations_stripped"] == 0
    assert result["verification"]["flags"] == []


def test_unresolvable_citation_stripped_and_downgraded():
    draft = _draft([{
        "id": "REQ-001", "priority": "high", "score": "COVERED",
        "response_text": "Proven scale [DOC-001]. We also hold FedRAMP [DOC-099].",
        "evidence_citations": "old", "gap_note": None,
    }])
    result = verify(draft, EVIDENCE_MAP)
    req = result["requirements"][0]
    assert req["score"] == "PARTIAL", "COVERED must downgrade when a citation is stripped"
    assert "[DOC-099]" not in req["response_text"]
    assert "[DOC-001]" in req["response_text"]
    assert "DOC-099" in result["verification"]["flags"][0]["note"]
    assert req["gap_note"], "Stripped citations must leave an actionable note"


def test_cross_requirement_citation_is_invalid():
    # DOC-010 exists in the corpus but was retrieved for REQ-002, not REQ-001 —
    # citing it from REQ-001 is exactly the laundering the Verifier must catch.
    draft = _draft([{
        "id": "REQ-001", "priority": "high", "score": "COVERED",
        "response_text": "Scale [DOC-001]. MTTR of 18 minutes [DOC-010].",
        "evidence_citations": "old", "gap_note": None,
    }])
    result = verify(draft, EVIDENCE_MAP)
    req = result["requirements"][0]
    assert "[DOC-010]" not in req["response_text"]
    assert req["score"] == "PARTIAL"


def test_fully_ungrounded_section_withheld_as_gap():
    draft = _draft([{
        "id": "REQ-002", "priority": "medium", "score": "COVERED",
        "response_text": "We are excellent at everything [DOC-077].",
        "evidence_citations": "old", "gap_note": None,
    }])
    result = verify(draft, EVIDENCE_MAP)
    req = result["requirements"][0]
    assert req["score"] == "GAP"
    assert req["response_text"] is None, "Ungrounded text must not ship"
    assert req["evidence_citations"] is None
    assert req["gap_note"]


def test_gap_sections_pass_through():
    draft = _draft([{
        "id": "REQ-003", "priority": "medium", "score": "GAP",
        "response_text": None, "evidence_citations": None,
        "gap_note": "Provide documentation.",
    }])
    result = verify(draft, EVIDENCE_MAP)
    assert result["requirements"][0]["score"] == "GAP"
    assert result["verification"]["citations_total"] == 0


def test_win_probability_recomputed_after_downgrades():
    draft = _draft([
        {"id": "REQ-001", "priority": "high", "score": "COVERED",
         "response_text": "Grounded [DOC-001].", "evidence_citations": "", "gap_note": None},
        {"id": "REQ-002", "priority": "high", "score": "COVERED",
         "response_text": "Ungrounded [DOC-077].", "evidence_citations": "", "gap_note": None},
    ])
    result = verify(draft, EVIDENCE_MAP)
    # REQ-002 drops to GAP: weights 3+3, earned 3*1.0 + 3*0.0 → 50%
    assert result["win_probability"] == 50
    assert result["gap_count"] == 1
