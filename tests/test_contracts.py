"""Tests for tools/contracts.py and the schema-retry layer in chat_json."""
import os

import pytest
from pydantic import ValidationError

os.environ["STUB_MODE"] = "true"
os.environ["RETRIEVAL_MODE"] = "local"

from tools import foundry_client
from tools.contracts import (
    DraftedProposal,
    EvidenceMap,
    IntakeExtraction,
    RequirementManifest,
    ScoredManifest,
    ScoreJudgement,
    VerifiedProposal,
)


# ── Per-call models ──────────────────────────────────────────────────────────

def test_intake_extraction_accepts_valid_payload():
    result = IntakeExtraction.model_validate({
        "requirements": [
            {"id": "REQ-001", "text": "Vendor must hold ISO 27001.",
             "priority": "high", "category": "legal"},
        ]
    })
    assert result.requirements[0].priority == "high"


def test_intake_extraction_coerces_unknown_vocab_to_defaults():
    result = IntakeExtraction.model_validate({
        "requirements": [
            {"text": "Something.", "priority": "URGENT!!", "category": "misc"},
        ]
    })
    assert result.requirements[0].priority == "medium"
    assert result.requirements[0].category == "other"


def test_intake_extraction_rejects_empty_text():
    with pytest.raises(ValidationError):
        IntakeExtraction.model_validate({"requirements": [{"text": ""}]})


def test_score_judgement_rejects_invalid_score():
    with pytest.raises(ValidationError):
        ScoreJudgement.model_validate({"score": "MAYBE", "confidence": 0.5})


def test_score_judgement_clamps_confidence():
    assert ScoreJudgement.model_validate({"score": "COVERED", "confidence": 1.7}).confidence == 1.0
    assert ScoreJudgement.model_validate({"score": "GAP", "confidence": "bad"}).confidence == 0.5


# ── Inter-stage contracts validate the stub pipeline payloads ────────────────

def test_stub_pipeline_payloads_honour_contracts():
    from agents.drafter_agent import run as drafter_run
    from agents.intake_agent import run as intake_run
    from agents.research_agent import run as research_run
    from agents.scorer_agent import run as scorer_run
    from agents.verifier import run as verifier_run
    from tools.doc_intelligence import parse_rfp

    manifest = intake_run(parse_rfp("demo/sample_rfp.pdf"))
    manifest = RequirementManifest.model_validate(manifest).model_dump()

    evidence_map = research_run(manifest)
    evidence_map = EvidenceMap.model_validate(evidence_map).model_dump()

    scored = scorer_run(manifest, evidence_map)
    scored = ScoredManifest.model_validate(scored).model_dump()

    req_lookup = {r["id"]: r for r in manifest["requirements"]}
    for sr in scored["scored_requirements"]:
        orig = req_lookup.get(sr["id"], {})
        sr["text"] = orig.get("text") or sr["text"]
        sr["priority"] = orig.get("priority") or sr["priority"]
        sr["category"] = orig.get("category") or sr["category"]

    draft = drafter_run(scored, evidence_map, {"company_name": "Test Co"})
    draft = DraftedProposal.model_validate(draft).model_dump()

    verified = verifier_run(draft, evidence_map)
    verified = VerifiedProposal.model_validate(verified).model_dump()
    assert verified["verification"]["citations_total"] >= 0


def test_requirement_manifest_rejects_missing_id():
    with pytest.raises(ValidationError):
        RequirementManifest.model_validate({"requirements": [{"id": "", "text": "x"}]})


# ── chat_json schema retry ───────────────────────────────────────────────────

def test_chat_json_retries_once_on_schema_error(monkeypatch):
    replies = ['{"score": "MAYBE"}', '{"score": "COVERED", "confidence": 0.8}']
    calls = []

    def fake_chat(system_prompt, user_message, **kwargs):
        calls.append(user_message)
        return replies[len(calls) - 1]

    monkeypatch.setattr(foundry_client, "chat", fake_chat)
    result = foundry_client.chat_json("sys", "user", schema=ScoreJudgement)
    assert result["score"] == "COVERED"
    assert len(calls) == 2
    assert "Validation errors" in calls[1]


def test_chat_json_second_schema_failure_propagates(monkeypatch):
    monkeypatch.setattr(foundry_client, "chat",
                        lambda *a, **k: '{"score": "MAYBE"}')
    with pytest.raises(ValidationError):
        foundry_client.chat_json("sys", "user", schema=ScoreJudgement)


def test_chat_json_without_schema_returns_parsed_dict(monkeypatch):
    monkeypatch.setattr(foundry_client, "chat", lambda *a, **k: '{"anything": 1}')
    assert foundry_client.chat_json("sys", "user") == {"anything": 1}
