"""Stage 5: Verifier — deterministic citation verification. Deliberately not an LLM.

Citation verification is a trust mechanism; running it through a model would
reintroduce the failure mode it exists to catch. This stage:

1. resolves every inline [DOC-xxx] citation in every drafted section against
   the evidence actually retrieved for that requirement,
2. strips citations that don't resolve,
3. downgrades affected sections (COVERED → PARTIAL; ungrounded → GAP) with an
   explicit flag, and
4. recomputes the priority-weighted requirement coverage score from post-verification
   scores.

The result is that no claim survives this stage unless the pipeline can point
at the exact internal document it came from.
"""
import logging
import re

from agents.scorer_agent import PRIORITY_WEIGHTS, SCORE_CREDIT

logger = logging.getLogger(__name__)

CITATION_RE = re.compile(r"\[(DOC-\d{3})\]")


def run(draft: dict, evidence_map: dict) -> dict:
    """Verify a drafted proposal against the evidence map.

    Args:
        draft: output of drafter_agent.run() — includes "requirements"
        evidence_map: output of research_agent.run()

    Returns:
        The draft with citations verified/stripped, scores adjusted,
        aggregates recomputed, and a "verification" summary attached.
    """
    requirements = draft.get("requirements", [])
    flags = []
    citations_total = 0
    citations_verified = 0

    for req in requirements:
        result = _verify_requirement(req, evidence_map.get(req["id"], []))
        citations_total += result["cited_count"]
        citations_verified += result["verified_count"]
        if result["flag"]:
            flags.append(result["flag"])

    draft["coverage_score"] = _recompute_coverage_score(requirements)
    draft["gap_count"] = sum(1 for r in requirements if r.get("score") == "GAP")
    draft["verification"] = {
        "citations_total": citations_total,
        "citations_verified": citations_verified,
        "citations_stripped": citations_total - citations_verified,
        "flags": flags,
    }

    logger.info(
        f"Verifier: {citations_verified}/{citations_total} citations verified, "
        f"{len(flags)} section(s) flagged — "
        f"post-verification requirement coverage score {draft['coverage_score']}%"
    )
    return draft


def _verify_requirement(req: dict, evidence: list) -> dict:
    """Verify one drafted section in place. Returns counts and an optional flag."""
    response_text = req.get("response_text")
    if not response_text:
        return {"cited_count": 0, "verified_count": 0, "flag": None}

    allowed = {e["doc_id"]: e for e in evidence}
    cited = list(dict.fromkeys(CITATION_RE.findall(response_text)))
    valid = [c for c in cited if c in allowed]
    invalid = [c for c in cited if c not in allowed]

    req["verification"] = {"cited": cited, "verified": valid, "stripped": invalid}
    flag = None

    if invalid:
        for doc_id in invalid:
            response_text = response_text.replace(f"[{doc_id}]", "")
        response_text = re.sub(r"  +", " ", response_text).strip()
        req["response_text"] = response_text

        flag = {
            "id": req["id"],
            "stripped_citations": invalid,
            "note": (
                f"{req['id']}: citation(s) {', '.join(invalid)} did not resolve "
                f"to retrieved evidence and were removed."
            ),
        }
        logger.warning(f"Verifier: {flag['note']}")

        if req.get("score") == "COVERED":
            req["score"] = "PARTIAL"
        unverified_note = (
            "One or more drafted citations could not be verified against "
            "retrieved evidence and were removed — review this section."
        )
        req["gap_note"] = f"{req['gap_note']} {unverified_note}".strip() \
            if req.get("gap_note") else unverified_note

    if not valid:
        # A drafted section with no verifiable citation is ungrounded text —
        # it does not ship. The requirement is surfaced as a GAP instead.
        flag = {
            "id": req["id"],
            "stripped_citations": invalid,
            "note": (
                f"{req['id']}: drafted response had no verifiable citations "
                f"and was withheld."
            ),
        }
        logger.warning(f"Verifier: {flag['note']}")
        req["score"] = "GAP"
        req["response_text"] = None
        req["evidence_citations"] = None
        req["gap_note"] = req.get("gap_note") or (
            "The drafted response could not be grounded in retrieved evidence. "
            "Provide source documentation for this requirement."
        )
    else:
        # Canonical citation list, rebuilt from verified ids only.
        req["evidence_citations"] = "\n".join(
            f"[{doc_id}] {allowed[doc_id]['title']}" for doc_id in valid
        )

    return {"cited_count": len(cited), "verified_count": len(valid), "flag": flag}


def _recompute_coverage_score(requirements: list) -> int:
    """Same priority-weighted formula as the Scorer, on post-verification scores."""
    total_weight = 0
    earned = 0.0
    for req in requirements:
        weight = PRIORITY_WEIGHTS.get(req.get("priority", "medium"), 2)
        total_weight += weight
        earned += weight * SCORE_CREDIT.get(req.get("score", "GAP"), 0.0)
    return round(earned / total_weight * 100) if total_weight else 0
