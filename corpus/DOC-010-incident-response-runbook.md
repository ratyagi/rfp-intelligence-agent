---
doc_id: DOC-010
title: Managed Services Incident Response Runbook (Extract)
doc_type: runbook
date: 2025-10-01
---

# Incident Response Runbook — Managed Services (Extract)

**Owner:** Head of Service Operations
**Version:** 5.1 (October 2025)
**Scope:** All managed Azure environments under 24/7 support

## Service levels (standard government tier)

- **Availability SLA: 99.95%** for Tier-1 production workloads, measured
  monthly per workload group
- **MTTR target: under 30 minutes** for Priority 1 incidents
- Achieved MTTR, trailing 12 months across all government clients:
  **19 minutes average** (StateGov platform: 18 minutes, DOC-002)

## Monitoring and tooling

- **Azure Monitor** — metrics, alerting, and availability tests for all
  managed workloads; action groups page the 24/7 NOC
- **Microsoft Sentinel** — security telemetry, analytics rules, and SOAR
  playbooks for containment actions
- Log Analytics retention per client classification requirements

## Priority 1 incident procedure

1. Automated detection pages on-call engineer (24/7 NOC, Australian-based)
2. Incident commander assigned within 5 minutes; client notified within 15
3. Containment / failover decision within 20 minutes — regional failover to
   Australia Southeast is pre-approved for Tier-1 workloads
4. Post-incident review delivered to client within 5 business days

## Evidence of operation

Monthly SLA reports for the last 24 months show the 99.95% availability
target met or exceeded in every month across all managed government
environments (HealthGov post-migration: 99.97%, DOC-001).
