# Evidence Corpus

This directory is the **company evidence base** indexed into the Foundry IQ
knowledge base (and searched directly in `RETRIEVAL_MODE=local`). It represents
the internal knowledge of **Contoso Cloud Solutions Pty Ltd**, a fictional
Australian cloud services provider.

> **All content is fictional**, created for the Agents League hackathon demo.
> Every company, client, person, certificate number, and metric is invented.
> No confidential information is present (per the hackathon disclaimer).

## Document format

Each document is markdown with YAML front matter:

```yaml
---
doc_id: DOC-001          # stable citation key — the Verifier resolves citations against this
title: ...
doc_type: case_study | certification | policy | commercial | cv | runbook | proposal | reference
date: YYYY-MM-DD
---
```

The `doc_id` is the contract between the Drafter and the Verifier: drafted
sections may only cite `doc_id`s present in the retrieval results for that
requirement, and the Verifier strips anything that doesn't resolve.

## Coverage design (intentional)

The corpus is deliberately engineered against `demo/sample_rfp.pdf` so a demo
run shows all three outcomes:

- **COVERED** — most technical, commercial, team, and privacy requirements
  have strong, metric-rich evidence here.
- **PARTIAL** — containerisation/AKS (MR-5) has only a brief pilot mention
  in DOC-012.
- **GAP** — Indigenous Procurement Policy participation (MR-11) and
  quantum-safe cryptography planning (MR-12) have **no evidence anywhere**
  in this corpus. The pipeline must say so rather than invent it.
