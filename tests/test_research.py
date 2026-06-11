"""Tests for the retrieval layer and Research Agent (RETRIEVAL_MODE=local).

These tests run real BM25 retrieval over corpus/ — no canned responses.
They encode the corpus coverage design: covered requirements must retrieve
their intended documents, and the engineered gaps (Indigenous procurement,
quantum-safe cryptography) must return nothing.
"""
import os

import pytest

os.environ["RETRIEVAL_MODE"] = "local"

from agents.research_agent import run as research_run
from tools.retrieval import LocalRetriever, get_retriever

MIGRATION_QUERY = (
    "proven experience migrating Windows Server workloads to Azure IaaS and "
    "PaaS, minimum three completed migrations of 500 or more virtual machines, "
    "contactable client references"
)
GAP_QUERIES = [
    # MR-11: nothing in the corpus covers Indigenous procurement
    "Indigenous Procurement Policy minimum 10% contract value delivered "
    "through registered Indigenous businesses subcontractors suppliers",
    # MR-12: nothing in the corpus covers post-quantum cryptography
    "quantum-safe cryptography transition plan post-quantum algorithms 2030 "
    "crypto-agility key management",
]


@pytest.fixture(scope="module")
def retriever():
    return LocalRetriever()


def test_get_retriever_local_mode():
    assert isinstance(get_retriever(), LocalRetriever)


def test_result_shape(retriever):
    results = retriever.search(MIGRATION_QUERY)
    assert results, "Migration query must return evidence"
    for item in results:
        assert set(item) == {"doc_id", "title", "excerpt", "source_path", "score"}
        assert item["doc_id"].startswith("DOC-")
        assert item["excerpt"]
        assert item["source_path"].startswith("corpus/")
        assert item["score"] > 0


def test_migration_query_finds_case_studies(retriever):
    doc_ids = {r["doc_id"] for r in retriever.search(MIGRATION_QUERY)}
    assert doc_ids & {"DOC-001", "DOC-002", "DOC-003", "DOC-013"}, (
        f"Expected migration case studies / references, got {doc_ids}"
    )


def test_sla_query_finds_runbook(retriever):
    results = retriever.search(
        "99.95% availability SLA Tier-1 production workloads, monitoring, "
        "incident response, mean time to recovery MTTR under 30 minutes"
    )
    assert results and results[0]["doc_id"] == "DOC-010"


def test_compliance_query_finds_certifications(retriever):
    doc_ids = {r["doc_id"] for r in retriever.search(
        "data must remain within Australian Azure regions, ISO 27001 "
        "certification, IRAP assessment PROTECTED level ISM"
    )}
    assert {"DOC-004", "DOC-005"} & doc_ids


@pytest.mark.parametrize("query", GAP_QUERIES)
def test_engineered_gaps_return_no_evidence(retriever, query):
    assert retriever.search(query) == [], (
        "Gap requirements must return no evidence — returning weak matches "
        "here would let the pipeline fabricate coverage"
    )


def test_nonsense_query_returns_nothing(retriever):
    assert retriever.search("submarine telescope cafeteria llama orbit") == []


def test_research_agent_builds_evidence_map():
    manifest = {"requirements": [
        {"id": "REQ-001", "text": MIGRATION_QUERY, "priority": "high", "category": "technical"},
        {"id": "REQ-002", "text": GAP_QUERIES[0], "priority": "medium", "category": "legal"},
    ]}
    evidence_map = research_run(manifest)
    assert set(evidence_map) == {"REQ-001", "REQ-002"}
    assert evidence_map["REQ-001"], "Covered requirement must have evidence"
    assert evidence_map["REQ-002"] == [], "Gap requirement must have no evidence"
