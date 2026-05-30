# RFP Intelligence Agent

AI-powered five-agent pipeline that transforms a raw RFP PDF into a populated, citation-grounded Word proposal draft in under 90 seconds — running entirely inside Microsoft 365.

## Tracks

- **Enterprise Agents** (primary)
- **Reasoning Agents** (secondary)

## The Problem

Sales and BD teams spend 3–5 days on every RFP response, and win rates sit at 20–30% because proposals are generic. The relevant internal knowledge — past proposals, case studies, pricing, objections handled — is buried in SharePoint, Teams chats, and Outlook threads with no fast way to retrieve and apply it.

## The Solution

A five-agent pipeline orchestrated on Azure AI Foundry:

1. **Intake Agent** — parses the RFP with Azure AI Document Intelligence, extracts a structured requirement manifest (REQ-001, REQ-002…) with priority and category.
2. **Research Agent** — queries SharePoint, Teams, and Outlook via Microsoft Graph API for evidence matching each requirement.
3. **Scorer Agent** — scores each requirement COVERED / PARTIAL / GAP and calculates a win-probability estimate.
4. **Drafter Agent** — writes 100–200 word response sections with inline citations to real company documents; flags GAPs for human action.
5. **Review Agent** — posts an Adaptive Card to Teams with win probability and gap count; routes approved drafts to SharePoint.

The entry point is a **Copilot Studio agent** in Teams — one file drop, no terminal, no config.

## Setup

```bash
git clone <repo-url>
cd rfp-intelligence-agent
cp .env.example .env
# Fill in .env with your Azure and M365 credentials
pip install -r requirements.txt
# Run in STUB mode (no live Azure credentials needed)
STUB_MODE=true python -m agents.orchestrator
# Run tests
pytest tests/
```

## Architecture

```
User (Teams / Copilot Chat)
  └─► Copilot Studio agent
        └─► Azure AI Foundry orchestrator
              ├─► Agent 1: Azure AI Document Intelligence (PDF parse)
              ├─► Agent 2: Microsoft Graph API (SharePoint, Teams, Outlook)
              │           via MCP connector
              ├─► Agent 3: Foundry reasoning model — requirement scoring
              ├─► Agent 4: Foundry reasoning model + python-docx
              └─► Agent 5: Teams Adaptive Card + SharePoint output
```

## Microsoft Technologies Used

| Service | Purpose |
|---|---|
| Azure AI Foundry Agent Service | Multi-agent orchestration |
| Azure AI Document Intelligence | PDF/DOCX parsing (`prebuilt-layout`) |
| Microsoft Graph API | SharePoint, Teams, Outlook search |
| Microsoft Copilot Studio | Teams / Copilot Chat entry point |
| Microsoft Teams Adaptive Cards | Human-in-the-loop approval UX |
| SharePoint Online | Evidence retrieval + approved draft storage |
| Azure Entra ID | Auth for Graph API and Foundry |

## Team

[Your name / team here]

## Demo

[DEMO VIDEO — to be added]
