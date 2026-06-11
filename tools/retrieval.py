"""Evidence retrieval — one interface, two backends.

RETRIEVAL_MODE=foundry_iq  → Foundry IQ knowledge base (agentic retrieval,
                             powered by Azure AI Search). Used for the live demo.
RETRIEVAL_MODE=local       → BM25 ranking over corpus/ on disk. Real retrieval
                             over the same real corpus — used for development
                             and for anyone cloning the repo without Azure.

Both backends return the same shape:
    [{"doc_id", "title", "excerpt", "source_path", "score"}]

The doc_id values are the citation keys the Verifier resolves against.
"""
import json
import logging
import math
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

CORPUS_DIR = Path(__file__).parent.parent / "corpus"

# Local mode: results scoring below this fraction of the query's best hit are
# dropped, and queries whose best hit is weak return nothing at all. This is
# what lets the pipeline say "no evidence" instead of returning noise for
# requirements the corpus genuinely doesn't cover.
RELATIVE_SCORE_CUTOFF = 0.55
ABSOLUTE_SCORE_FLOOR = 6.0

_STOPWORDS = frozenset(
    "a an and are as at be by for from has have in is it its must of on or "
    "that the to with will within their this any all each per under no not "
    "than then there these those was were been being we our your they them "
    "if into out over also may can shall should would more most least very".split()
)


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9][a-z0-9+.-]*", text.lower()) if t not in _STOPWORDS]


def _parse_front_matter(raw: str) -> tuple[dict, str]:
    """Parse the simple `key: value` YAML front matter used by corpus docs."""
    meta = {}
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip()
            body = parts[2]
    return meta, body.strip()


class LocalRetriever:
    """BM25 over the markdown documents in corpus/."""

    K1 = 1.5
    B = 0.75

    def __init__(self, corpus_dir: Path = CORPUS_DIR):
        self._docs = []
        for path in sorted(corpus_dir.glob("DOC-*.md")):
            meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
            tokens = _tokenize(meta.get("title", "") + " " + body)
            self._docs.append({
                "doc_id": meta.get("doc_id", path.stem),
                "title": meta.get("title", path.stem),
                "source_path": str(path.relative_to(corpus_dir.parent)),
                "body": body,
                "tokens": tokens,
                "tf": {t: tokens.count(t) for t in set(tokens)},
            })
        if not self._docs:
            raise FileNotFoundError(f"No corpus documents found in {corpus_dir}")

        self._avg_len = sum(len(d["tokens"]) for d in self._docs) / len(self._docs)
        n = len(self._docs)
        self._idf = {}
        for doc in self._docs:
            for term in doc["tf"]:
                self._idf[term] = self._idf.get(term, 0) + 1
        for term, df in self._idf.items():
            self._idf[term] = math.log(1 + (n - df + 0.5) / (df + 0.5))

    def search(self, query: str, top: int = 3) -> list[dict]:
        query_terms = _tokenize(query)
        scored = []
        for doc in self._docs:
            score = 0.0
            for term in query_terms:
                tf = doc["tf"].get(term, 0)
                if tf == 0:
                    continue
                idf = self._idf.get(term, 0.0)
                norm = tf * (self.K1 + 1) / (
                    tf + self.K1 * (1 - self.B + self.B * len(doc["tokens"]) / self._avg_len)
                )
                score += idf * norm
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        if not scored or scored[0][0] < ABSOLUTE_SCORE_FLOOR:
            return []

        best = scored[0][0]
        results = []
        for score, doc in scored[:top]:
            if score < best * RELATIVE_SCORE_CUTOFF:
                break
            results.append({
                "doc_id": doc["doc_id"],
                "title": doc["title"],
                "excerpt": self._best_excerpt(doc["body"], query_terms),
                "source_path": doc["source_path"],
                "score": round(score, 2),
            })
        return results

    @staticmethod
    def _best_excerpt(body: str, query_terms: list[str], max_chars: int = 320) -> str:
        """Return the paragraph with the highest query-term overlap."""
        paragraphs = [p.strip() for p in body.split("\n\n") if len(p.strip()) > 60]
        if not paragraphs:
            return body[:max_chars]
        term_set = set(query_terms)
        best = max(paragraphs, key=lambda p: len(term_set & set(_tokenize(p))))
        best = re.sub(r"[#*|>-]+", " ", best)
        best = re.sub(r"\s+", " ", best).strip()
        return best[:max_chars]


class FoundryIQRetriever:
    """Agentic retrieval against a Foundry IQ knowledge base.

    Foundry IQ knowledge bases are powered by the Azure AI Search agentic
    retrieval engine; this client calls the knowledge base's retrieve API.
    Setup (index + corpus upload + knowledge base) is done once by
    scripts/setup_foundry_iq.py.
    """

    API_VERSION = "2025-05-01-preview"

    def __init__(self):
        self._endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
        self._api_key = os.getenv("AZURE_SEARCH_API_KEY", "")
        self._knowledge_base = os.getenv("FOUNDRY_IQ_KNOWLEDGE_BASE", "rfp-evidence")
        if not self._endpoint or not self._api_key:
            raise EnvironmentError(
                "RETRIEVAL_MODE=foundry_iq requires AZURE_SEARCH_ENDPOINT and "
                "AZURE_SEARCH_API_KEY in .env (run scripts/setup_foundry_iq.py first)"
            )

    def search(self, query: str, top: int = 3) -> list[dict]:
        url = (
            f"{self._endpoint}/agents/{self._knowledge_base}/retrieve"
            f"?api-version={self.API_VERSION}"
        )
        payload = {
            "messages": [{
                "role": "user",
                "content": [{"type": "text", "text": query}],
            }],
            "targetIndexParams": [{
                "indexName": f"{self._knowledge_base}-index",
                "rerankerThreshold": 1.5,
                "maxDocsForReranker": top * 10,
            }],
        }
        response = requests.post(
            url,
            headers={"api-key": self._api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Foundry IQ retrieval failed: {response.status_code} {response.text[:500]}"
            )

        body = response.json()
        results = []
        for ref in body.get("references", [])[:top]:
            source = ref.get("sourceData") or {}
            results.append({
                "doc_id": source.get("doc_id", ref.get("docKey", "")),
                "title": source.get("title", ""),
                "excerpt": (source.get("content") or "")[:320],
                "source_path": source.get("source_path", ""),
                "score": ref.get("rerankerScore", 0.0),
            })
        # The retrieve API can also return synthesized grounding text without
        # references; we only trust explicit references because doc_id is the
        # contract the Verifier enforces.
        return results


def get_retriever():
    mode = os.getenv("RETRIEVAL_MODE", "local").lower()
    if mode == "foundry_iq":
        logger.info("retrieval: using Foundry IQ knowledge base")
        return FoundryIQRetriever()
    if mode == "local":
        logger.info("retrieval: using local BM25 over corpus/")
        return LocalRetriever()
    raise ValueError(f"Unknown RETRIEVAL_MODE '{mode}' — expected 'foundry_iq' or 'local'")
