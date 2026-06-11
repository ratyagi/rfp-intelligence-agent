"""Agent 2: Research Agent — retrieves evidence for each requirement.

Evidence comes from the Foundry IQ knowledge base (RETRIEVAL_MODE=foundry_iq)
or from local BM25 over corpus/ (RETRIEVAL_MODE=local). Retrieval is
deterministic and judgement-free by design: deciding whether evidence is
*sufficient* is the Scorer's job, and verifying citations against what was
actually retrieved is the Verifier's job.
"""
import logging

from tools.retrieval import get_retriever

logger = logging.getLogger(__name__)

EVIDENCE_PER_REQUIREMENT = 3


def run(manifest: dict) -> dict:
    """Build an evidence map for all requirements.

    Args:
        manifest: output of intake_agent.run() — {"requirements": [...]}

    Returns:
        {"REQ-001": [{"doc_id", "title", "excerpt", "source_path", "score"}], ...}
        An empty list means the corpus holds no relevant evidence — that is a
        finding (the Scorer turns it into a GAP), not an error.
    """
    requirements = manifest.get("requirements", [])
    retriever = get_retriever()
    evidence_map = {}

    for req in requirements:
        req_id = req["id"]
        evidence = retriever.search(req["text"], top=EVIDENCE_PER_REQUIREMENT)
        evidence_map[req_id] = evidence
        logger.info(
            f"ResearchAgent: {req_id} — {len(evidence)} evidence item(s)"
            + (f" [{', '.join(e['doc_id'] for e in evidence)}]" if evidence else " (no corpus coverage)")
        )

    return evidence_map
