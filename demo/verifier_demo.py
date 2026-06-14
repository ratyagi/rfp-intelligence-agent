"""Adversarial demo: prove the Verifier catches a fabricated citation.

The Verifier is the project's trust mechanism, and it is deliberately not an
LLM. This script hands it a drafted proposal where the model has cited a
document that was never retrieved (DOC-999), then runs the real, unmodified
Verifier (agents/verifier.py) and shows what it does:

  - a citation that does not resolve to retrieved evidence is STRIPPED, and
  - a section left with no valid citation is WITHHELD and surfaced as a GAP.

Run:  python -m demo.verifier_demo
No API calls, no credentials — it exercises the deterministic stage directly.
"""
import copy

from agents.verifier import run as verify

# What the Research stage actually retrieved (the ground truth the Verifier
# checks against). DOC-999 is deliberately absent.
EVIDENCE_MAP = {
    "REQ-001": [{"doc_id": "DOC-001", "title": "Case Study — HealthGov Azure Migration",
                 "excerpt": "Migrated 620 VMs with zero unplanned downtime."}],
    "REQ-002": [{"doc_id": "DOC-004", "title": "ISO/IEC 27001:2022 Certification",
                 "excerpt": "Certificate current through 2026."}],
}

# A drafted proposal where the model fabricated citations.
DRAFT = {
    "company_name": "Contoso Cloud Solutions",
    "rfp_title": "Adversarial Verifier Demo",
    "submission_date": "14 June 2026",
    "executive_summary": "Demonstration of citation verification.",
    "coverage_score": 100,
    "requirements": [
        {
            "id": "REQ-001", "text": "Prove 500+ VM migration experience.",
            "priority": "high", "category": "technical", "confidence": 0.9, "score": "COVERED",
            # One real citation (DOC-001) and one fabricated (DOC-999).
            "response_text": "We have migrated 620 VMs with zero downtime [DOC-001], "
                             "and hold a partnership award for it [DOC-999].",
            "evidence_citations": "[DOC-001]\n[DOC-999]", "gap_note": None,
        },
        {
            "id": "REQ-002", "text": "Hold ISO 27001 certification.",
            "priority": "high", "category": "legal", "confidence": 0.9, "score": "COVERED",
            # ONLY a fabricated citation — nothing real backs this section.
            "response_text": "We are certified to the highest global standard [DOC-999].",
            "evidence_citations": "[DOC-999]", "gap_note": None,
        },
    ],
}


def _line(c="-"):
    print(c * 68)


def main() -> None:
    before = copy.deepcopy(DRAFT)
    after = verify(copy.deepcopy(DRAFT), EVIDENCE_MAP)

    print("\nADVERSARIAL CITATION TEST — the real Verifier, no LLM\n")
    for b, a in zip(before["requirements"], after["requirements"]):
        _line("=")
        print(f"{b['id']}  ({b['priority']} priority)")
        print(f"\n  DRAFTED BY THE MODEL ({b['score']}):")
        print(f"    {b['response_text']}")
        v = a.get("verification", {})
        print(f"\n  VERIFIER RESULT  ->  {a['score']}")
        print(f"    cited:    {v.get('cited', [])}")
        print(f"    verified: {v.get('verified', [])}")
        print(f"    STRIPPED: {v.get('stripped', [])}")
        if a.get("response_text"):
            print(f"\n  SHIPPED TEXT (fabricated citation removed):")
            print(f"    {a['response_text']}")
        else:
            print(f"\n  SECTION WITHHELD — no verifiable citation remained.")
            print(f"    ACTION REQUIRED: {a.get('gap_note')}")
        print()

    _line("=")
    summary = after["verification"]
    print(f"\nSUMMARY: {summary['citations_verified']}/{summary['citations_total']} "
          f"citations verified, {summary['citations_stripped']} stripped.")
    print(f"Coverage score recomputed on POST-verification scores: {after['coverage_score']}%")
    print("\nNo fabricated citation reached the proposal. By construction, not by hope.\n")


if __name__ == "__main__":
    main()
