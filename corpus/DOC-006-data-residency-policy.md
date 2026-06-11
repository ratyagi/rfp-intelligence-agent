---
doc_id: DOC-006
title: Data Residency and Sovereignty Policy
doc_type: policy
date: 2025-01-10
---

# Data Residency and Sovereignty Policy

**Owner:** Chief Information Security Officer
**Version:** 3.2 (January 2025)
**Applies to:** All client engagements involving Australian government or
regulated-industry data

## Policy

1. **Australian regions only.** All client workloads and data classified
   OFFICIAL or above are deployed exclusively to Azure **Australia East**
   (primary) and **Australia Southeast** (secondary/DR). Deployment to any
   other region requires written CISO exemption; no exemption has ever been
   granted for government data.
2. **Replication boundaries.** Geo-replication, backup, and DR targets are
   constrained by Azure Policy to the two Australian regions. Policy
   assignments are audited monthly.
3. **Support access.** Administrative access is restricted to
   Australian-based, security-cleared personnel. Customer Lockbox is
   enabled for all government tenants.
4. **Metadata.** Where service metadata may transit other regions, this is
   documented per service in the engagement's data flow register and
   disclosed to the client before go-live.

## Enforcement

- Azure Policy deny-rules on region selection, validated in CI for all
  infrastructure-as-code deployments
- Quarterly compliance attestation to each government client
- Verified during the June 2025 IRAP assessment (DOC-005)
