"""One-time setup for the Foundry IQ knowledge base over corpus/.

Foundry IQ knowledge bases are powered by the Azure AI Search agentic
retrieval engine. This script:

  1. creates (or updates) the search index that backs the knowledge base
  2. uploads every corpus document, preserving doc_id as the citation key
  3. creates (or updates) the knowledge base, bound to the Foundry model
     deployment that plans and reranks retrieval queries

Requires in .env:
  AZURE_SEARCH_ENDPOINT       https://<service>.search.windows.net
  AZURE_SEARCH_API_KEY        admin key (setup needs write access)
  AZURE_FOUNDRY_ENDPOINT      Foundry / Azure OpenAI resource endpoint
  AZURE_FOUNDRY_API_KEY
  FOUNDRY_MODEL_DEPLOYMENT    e.g. gpt-4o
  FOUNDRY_IQ_KNOWLEDGE_BASE   knowledge base name (default: rfp-evidence)

Note: agentic retrieval requires the search service to have semantic ranker
enabled (Basic tier or above).

Usage:
    python scripts/setup_foundry_iq.py
"""
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.retrieval import _parse_front_matter  # noqa: E402

load_dotenv()

API_VERSION = "2025-05-01-preview"
CORPUS_DIR = Path(__file__).parent.parent / "corpus"


def _require_env(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise SystemExit(f"ERROR: {name} must be set in .env — see script docstring.")
    return value


def main() -> None:
    search_endpoint = _require_env("AZURE_SEARCH_ENDPOINT").rstrip("/")
    search_key = _require_env("AZURE_SEARCH_API_KEY")
    foundry_endpoint = _require_env("AZURE_FOUNDRY_ENDPOINT").rstrip("/")
    foundry_key = _require_env("AZURE_FOUNDRY_API_KEY")
    deployment = os.getenv("FOUNDRY_MODEL_DEPLOYMENT", "gpt-4o")
    kb_name = os.getenv("FOUNDRY_IQ_KNOWLEDGE_BASE", "rfp-evidence")
    index_name = f"{kb_name}-index"

    headers = {"api-key": search_key, "Content-Type": "application/json"}

    # ── 1. Index ─────────────────────────────────────────────────────────
    index_def = {
        "name": index_name,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "doc_id", "type": "Edm.String", "filterable": True, "retrievable": True},
            {"name": "title", "type": "Edm.String", "searchable": True, "retrievable": True},
            {"name": "doc_type", "type": "Edm.String", "filterable": True, "retrievable": True},
            {"name": "date", "type": "Edm.String", "retrievable": True},
            {"name": "source_path", "type": "Edm.String", "retrievable": True},
            {"name": "content", "type": "Edm.String", "searchable": True, "retrievable": True},
        ],
        "semantic": {
            "defaultConfiguration": "default",
            "configurations": [{
                "name": "default",
                "prioritizedFields": {
                    "titleField": {"fieldName": "title"},
                    "prioritizedContentFields": [{"fieldName": "content"}],
                    "prioritizedKeywordsFields": [{"fieldName": "doc_type"}],
                },
            }],
        },
    }
    resp = requests.put(
        f"{search_endpoint}/indexes/{index_name}?api-version={API_VERSION}",
        headers=headers, json=index_def, timeout=60,
    )
    if resp.status_code not in (200, 201, 204):
        raise SystemExit(f"Index creation failed: {resp.status_code} {resp.text[:800]}")
    print(f"✓ Index '{index_name}' ready")

    # ── 2. Upload corpus ─────────────────────────────────────────────────
    actions = []
    for path in sorted(CORPUS_DIR.glob("DOC-*.md")):
        meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
        doc_id = meta.get("doc_id", path.stem)
        actions.append({
            "@search.action": "mergeOrUpload",
            "id": doc_id,
            "doc_id": doc_id,
            "title": meta.get("title", path.stem),
            "doc_type": meta.get("doc_type", "other"),
            "date": meta.get("date", ""),
            "source_path": str(path.relative_to(CORPUS_DIR.parent)),
            "content": body,
        })
    if not actions:
        raise SystemExit(f"No corpus documents found in {CORPUS_DIR}")

    resp = requests.post(
        f"{search_endpoint}/indexes/{index_name}/docs/index?api-version={API_VERSION}",
        headers=headers, json={"value": actions}, timeout=120,
    )
    if resp.status_code not in (200, 201):
        raise SystemExit(f"Corpus upload failed: {resp.status_code} {resp.text[:800]}")
    failures = [r for r in resp.json().get("value", []) if not r.get("status")]
    if failures:
        raise SystemExit(f"Some documents failed to index: {failures}")
    print(f"✓ Uploaded {len(actions)} corpus documents")

    # ── 3. Knowledge base (agentic retrieval agent) ──────────────────────
    kb_def = {
        "name": kb_name,
        "models": [{
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": foundry_endpoint,
                "deploymentId": deployment,
                "modelName": deployment,
                "apiKey": foundry_key,
            },
        }],
        "targetIndexes": [{
            "indexName": index_name,
            "defaultRerankerThreshold": 1.5,
        }],
    }
    resp = requests.put(
        f"{search_endpoint}/agents/{kb_name}?api-version={API_VERSION}",
        headers=headers, json=kb_def, timeout=60,
    )
    if resp.status_code not in (200, 201, 204):
        raise SystemExit(f"Knowledge base creation failed: {resp.status_code} {resp.text[:800]}")
    print(f"✓ Knowledge base '{kb_name}' ready")
    print("\nSetup complete. Set RETRIEVAL_MODE=foundry_iq in .env to use it.")


if __name__ == "__main__":
    main()
