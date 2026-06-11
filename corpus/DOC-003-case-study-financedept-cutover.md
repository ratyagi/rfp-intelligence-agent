---
doc_id: DOC-003
title: Case Study — FinanceDept Agency Core Systems Migration
doc_type: case_study
date: 2025-11-20
---

# Case Study: FinanceDept Agency — Core Systems Migration to Azure

**Client:** FinanceDept Agency (federal financial administration agency)
**Engagement:** Migration of core financial systems to Azure IaaS/PaaS
**Duration:** 9 months (Mar 2025 – Nov 2025)
**Contract value:** AUD 4.9M

## Scope

Migration of **510 virtual machines** hosting the agency's general ledger,
budget management, and reporting platforms — systems with a hard requirement
that cutover windows never exceed 4 hours due to overnight batch processing.

## Approach

- Azure Site Recovery with rehearsal cutovers two weeks before each
  production cutover
- Batch-window-aware scheduling: all cutovers executed between end-of-batch
  and start-of-business
- Rollback plans tested and timed for every workload group

## Outcomes

- Production cutover of the core ledger platform completed in
  **2 hours 30 minutes** — well inside the 4-hour contractual window
- **Zero data loss**, confirmed by the agency's operations team through
  transaction-level reconciliation
- SQL workloads re-platformed to Azure SQL Managed Instance, reducing
  database administration effort by an estimated 35%
- Engagement delivered on the agreed fixed price with no variations

## Reference

FinanceDept Agency has consented to reference calls for Commonwealth
procurement processes. See the client reference register (DOC-013).
