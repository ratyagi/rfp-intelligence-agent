"""Tests for AzureSearchRetriever — mocked HTTP, no live service needed."""
import os

import pytest

os.environ["STUB_MODE"] = "true"

from tools import retrieval
from tools.retrieval import AzureSearchRetriever, get_retriever


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def _make_retriever(monkeypatch):
    monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://unit.search.windows.net")
    monkeypatch.setenv("AZURE_SEARCH_API_KEY", "unit-test-key")
    return AzureSearchRetriever()


def _semantic_hit(doc_id, score, reranker=None):
    hit = {
        "doc_id": doc_id,
        "title": f"Title {doc_id}",
        "content": "Some grounded evidence text " * 20,
        "source_path": f"corpus/{doc_id}.md",
        "@search.score": score,
    }
    if reranker is not None:
        hit["@search.rerankerScore"] = reranker
    return hit


def test_requires_endpoint_and_key(monkeypatch):
    monkeypatch.delenv("AZURE_SEARCH_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_SEARCH_API_KEY", raising=False)
    with pytest.raises(EnvironmentError):
        AzureSearchRetriever()


def test_semantic_results_mapped_and_thresholded(monkeypatch):
    retriever = _make_retriever(monkeypatch)
    payload = {"value": [
        _semantic_hit("DOC-001", 8.0, reranker=2.4),
        _semantic_hit("DOC-002", 7.0, reranker=1.9),
        _semantic_hit("DOC-003", 6.0, reranker=0.9),  # below 1.5 floor → dropped
    ]}
    monkeypatch.setattr(retrieval.requests, "post",
                        lambda *a, **k: FakeResponse(200, payload))

    results = retriever.search("uptime SLA evidence")
    assert [r["doc_id"] for r in results] == ["DOC-001", "DOC-002"]
    assert results[0]["score"] == 2.4
    assert len(results[0]["excerpt"]) <= 320
    assert results[0]["source_path"] == "corpus/DOC-001.md"


def test_semantic_unavailable_falls_back_to_fulltext(monkeypatch):
    retriever = _make_retriever(monkeypatch)
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        if json.get("queryType") == "semantic":
            return FakeResponse(400, text="Semantic search is not enabled for this service")
        return FakeResponse(200, {"value": [
            _semantic_hit("DOC-004", 9.0),
            _semantic_hit("DOC-005", 2.0),  # < 9.0 * 0.55 → dropped by relative cutoff
        ]})

    monkeypatch.setattr(retrieval.requests, "post", fake_post)
    results = retriever.search("data residency")
    assert [r["doc_id"] for r in results] == ["DOC-004"]
    assert retriever._semantic is False
    # Subsequent searches skip the semantic attempt entirely.
    results = retriever.search("another query")
    assert all(c.get("queryType") != "semantic" for c in calls[2:])


def test_empty_results_mean_no_evidence(monkeypatch):
    retriever = _make_retriever(monkeypatch)
    monkeypatch.setattr(retrieval.requests, "post",
                        lambda *a, **k: FakeResponse(200, {"value": []}))
    assert retriever.search("requirement with no corpus coverage") == []


def test_get_retriever_selects_azure_search(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_MODE", "azure_search")
    monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://unit.search.windows.net")
    monkeypatch.setenv("AZURE_SEARCH_API_KEY", "unit-test-key")
    assert isinstance(get_retriever(), AzureSearchRetriever)
