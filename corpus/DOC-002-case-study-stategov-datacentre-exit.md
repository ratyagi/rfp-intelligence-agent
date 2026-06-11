---
doc_id: DOC-002
title: Case Study — StateGov Authority Cloud Transition Program
doc_type: case_study
date: 2025-09-30
---

# Case Study: StateGov Authority — Cloud Transition Program

**Client:** StateGov Authority (state government shared-services provider)
**Engagement:** Migration of shared-services platform to Azure
**Duration:** 11 months (Oct 2024 – Sep 2025)
**Contract value:** AUD 6.4M

## Scope

Migration of **540 virtual machines** (Windows Server 2016, plus 60 RHEL),
28 line-of-business applications serving 9 state agencies, and an Exchange
hybrid estate, from a leased datacentre due for closure.

## Approach

- Azure Site Recovery as the primary replication and cutover mechanism
- Application-aligned migration waves with agency-by-agency signoff
- Automated post-cutover validation suites per application
- 24/7 hypercare for 2 weeks after each wave

## Outcomes

- All 540 VMs migrated with **zero data loss** (verified by per-wave
  reconciliation reports signed by StateGov operations)
- Availability of **99.96%** in the most recent quarter
- **Mean time to recovery (MTTR) of 18 minutes** average across all
  production incidents in the first 12 months of operation
- Datacentre lease exited on schedule, avoiding AUD 1.1M in renewal costs

## Operational notes

The StateGov platform is operated under our standard incident response
runbook (DOC-010), with Azure Monitor and Microsoft Sentinel providing
monitoring and security telemetry.
