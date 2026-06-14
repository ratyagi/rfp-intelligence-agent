# Submission copy: Agents League @ AI Skills Fest

## Challenge / Track
**Reasoning Agents (Microsoft Foundry).** The project is a multi-step reasoning
pipeline that decomposes a complex document into atomic decisions, and it
integrates the required Microsoft IQ layer through Foundry IQ.

## Tagline
**The RFP co-pilot that refuses to make things up.**

Alternates:
- Draft a grounded RFP response in minutes, where every citation is verified or stripped.
- It knows what it does not know, and it tells you before you submit.

## Keywords
RFP automation, Microsoft Foundry, Foundry IQ, Azure AI Search, agentic pipeline,
multi-step reasoning, grounded generation, citation verification, retrieval augmented
generation, proposal drafting, bid management, human in the loop, hallucination control

## Description

**The problem.** Every RFP response is a 3 to 5 day grind. Teams read hundreds of
requirements, dig through old proposals and case studies for proof, and write each
section by hand. Win rates still sit around 20 to 30 percent. And the moment you let
an AI draft it unsupervised, a new risk shows up: it invents capabilities the company
does not have. In a signed government tender, a made up claim is not a typo. It is a
breach of contract. The hard part was never the writing. It is making every claim
provably trace back to a real document.

**The solution.** RFP Intelligence Agent turns a raw RFP PDF into a citation grounded
draft proposal, and it treats trust as the product. It is a six stage pipeline built
on Microsoft Foundry. Three stages use gpt 4.1 to reason: extract every requirement,
score how well your evidence covers each one, and draft the response sections. Three
stages are deterministic code with no LLM: retrieval from Foundry IQ, citation
verification, and document assembly. That split is the entire idea. The model does the
judgement. Plain code does the things you have to be able to trust.

**The part that matters.** A deterministic Verifier checks every citation the AI writes
against the documents actually retrieved from your knowledge base. If a citation does
not resolve, it is stripped. If a section is left with no valid citation, it is withheld
and flagged for a human. In our live run, 52 of 52 citations resolved to real source
documents, with zero stripped. When the evidence base does not cover a requirement, the
agent flags a gap instead of bluffing. It knows what it does not know.

**What you get.** A finished Word proposal, a machine readable Bid Decision Report that
shows the full reasoning trace for every requirement (evidence considered, score and
confidence, verification outcome, action required), and a human approval card. Nothing
ships without a person deciding.

**Built on Microsoft.** Microsoft Foundry (gpt 4.1) for reasoning, Foundry IQ over
Azure AI Search for grounded retrieval, Pydantic contracts validated at every stage
boundary, and a rate limit aware client. The whole thing runs on a zero dollar free
tier setup, which proves it does not need an uncapped cloud bill to work.

**Honest scope.** This is a proof of concept on a synthetic RFP and a synthetic
evidence corpus. The Verifier guarantees citation provenance (every citation points to
a real retrieved document). Claim level fact checking, and live delivery into Teams and
SharePoint, are on the roadmap. We would rather show you exactly what it does than
oversell what it does not.
