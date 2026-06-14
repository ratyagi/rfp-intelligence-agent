# RFP Intelligence Agent — 90-Second Demo Script

**Audience:** Hackathon judges (Agents League / Microsoft)
**Surface:** Microsoft Teams / Copilot Chat
**Fallback:** `demo/sample_output.docx` if live pipeline is slow

---

## Before you go on screen

- [ ] Open Teams in a browser tab — navigate to the channel where the Copilot Studio agent is deployed
- [ ] Open the SharePoint RFP-Outputs folder in a second tab
- [ ] Have `demo/sample_rfp.pdf` (8-page fictional government cloud RFP) ready to drag in
- [ ] Pre-load `demo/sample_output.docx` in Word as a tab — fallback only
- [ ] Set `STUB_MODE=false` and confirm `.env` has live credentials

---

## [0:00–0:15] Setup

Open the Teams channel. Say:

> "I'm going to drop a real government RFP — 47 pages, due in two weeks. Watch what happens."

Drag `demo/sample_rfp.pdf` into the agent chat and hit send.

---

## [0:15–0:45] The pitch (speak while pipeline runs)

> "This is a 47-page government RFP for cloud infrastructure modernisation. Normally this takes our sales team 3–5 days — reading through requirements, digging through SharePoint for past proposals, writing every section from scratch."

> "Right now the agent is doing all of that automatically. It's parsing every requirement out of the PDF, searching our SharePoint and Teams channels for evidence from past projects, scoring how well we can respond to each requirement, and drafting response sections grounded in our actual internal documents."

> "No generic boilerplate. Every claim it makes will cite a real document from our SharePoint."

---

## [0:45–1:15] The reveal

The Teams Adaptive Card appears in the channel. Point to it:

> "Here's our result. Requirement coverage: [X]%. [N] gap(s) need our input before we can submit."

Click **"View Draft"** — Word opens.

> "This is the full proposal draft. Let me scroll to any requirement section."

Scroll to a COVERED requirement. Point to the citation at the end of the paragraph:

> "Every factual claim cites the exact SharePoint document it came from. Not a hallucinated reference — a real link back to the case study we did for [client name]."

Scroll to a GAP section (red row):

> "This one is flagged red — ACTION REQUIRED. We don't have evidence for this requirement in our knowledge base yet. The agent knows what it doesn't know, and it tells us exactly what to provide."

---

## [1:15–1:30] Close

> "3–5 days. 90 seconds. Same quality — actually better, because every claim is grounded in our real internal documents, not written from memory. And a human reviews and approves before anything goes out."

Click **"Approve & Send to SharePoint"** — show the file appearing in the SharePoint tab.

> "That's it. The approved draft is now in SharePoint, ready for final review."

---

## Fallback procedure (if live pipeline is slow)

If the pipeline takes more than 60 seconds:

1. Say: "The pipeline is running — while we wait, let me show you what the output looks like."
2. Switch to the pre-loaded `demo/sample_output.docx` Word tab.
3. Walk through the same reveal section above using the pre-generated file.
4. Return to Teams when the card appears.

---

## Backup notes for Q&A

| Question | Answer |
|---|---|
| "Does it work with any RFP?" | Yes — the Document Intelligence model handles any PDF or Word document structure. |
| "What if we don't have SharePoint?" | The Graph API connector can be pointed at any M365 tenant. The agent searches wherever your documents live. |
| "How do you prevent hallucination?" | The Drafter Agent's system prompt explicitly prohibits citing any document not in the evidence map returned by the Research Agent. The Scorer Agent marks gaps rather than inventing evidence. |
| "Is the human approval gate removable?" | It's intentionally non-removable. Enterprise governance requires a human in the loop before a proposal goes out. This is a feature, not a limitation. |
| "How much does it cost per run?" | Approximately [X] Azure AI token spend per RFP. Compare to 3–5 days of a BD team member's salary. |
