"""Generate demo/sample_rfp.pdf — a realistic fictional government RFP.

The requirements in this RFP are deliberately engineered against the evidence
corpus in corpus/ so a pipeline run produces a meaningful mix of outcomes:
most requirements COVERED, MR-5 PARTIAL (weak evidence only), and MR-11 /
MR-12 genuine GAPs (no evidence exists in the corpus).

Usage:
    pip install fpdf2
    python scripts/generate_sample_rfp.py
"""
from pathlib import Path

from fpdf import FPDF

OUTPUT = Path(__file__).parent.parent / "demo" / "sample_rfp.pdf"

REF = "GOV-2026-ICT-0042"
AGENCY = "Department of Digital Transformation (DDT)"


class RfpPdf(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("helvetica", "I", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 6, f"{REF} - Cloud Infrastructure Modernisation Services - OFFICIAL", align="L")
        self.ln(10)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 10, f"Page {self.page_no()} of {{nb}}", align="C")
        self.set_text_color(0, 0, 0)

    def mc(self, h, text, align="L"):
        self.multi_cell(0, h, text, align=align, new_x="LMARGIN", new_y="NEXT")

    def h1(self, text):
        self.set_font("helvetica", "B", 14)
        self.ln(4)
        self.mc(7, text)
        self.ln(2)

    def h2(self, text):
        self.set_font("helvetica", "B", 11)
        self.ln(2)
        self.mc(6, text)
        self.ln(1)

    def body(self, text):
        self.set_font("helvetica", "", 10)
        self.mc(5.4, text)
        self.ln(2)

    def clause(self, ref, priority, text):
        self.set_font("helvetica", "B", 10)
        self.mc(5.4, f"{ref} ({priority})")
        self.set_font("helvetica", "", 10)
        self.mc(5.4, text)
        self.ln(2.5)


def build() -> None:
    pdf = RfpPdf(format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)

    # ── Cover page ───────────────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, "AUSTRALIAN GOVERNMENT (FICTIONAL)", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("helvetica", "B", 20)
    pdf.mc(10, "REQUEST FOR PROPOSAL", align="C")
    pdf.set_font("helvetica", "B", 16)
    pdf.mc(9, "Cloud Infrastructure Modernisation Services", align="C")
    pdf.ln(8)
    pdf.set_font("helvetica", "", 12)
    pdf.mc(
        7,
        f"RFP Reference: {REF}\n"
        f"Issuing Agency: {AGENCY}\n"
        "Issue Date: 12 May 2026\n"
        "Submission Deadline: 17:00 AEST, 30 June 2026\n"
        "Lodgement: AusTender portal",
        align="C",
    )
    pdf.ln(14)
    pdf.set_font("helvetica", "I", 9)
    pdf.mc(
        5,
        "This is a fictional procurement document created for a software "
        "demonstration. The issuing agency, requirements, and all details are "
        "invented. It is modelled on the structure of real Australian "
        "government ICT procurement documents.",
        align="C",
    )

    # ── 1. Introduction ──────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("1. Introduction and Background")
    pdf.body(
        f"The {AGENCY} delivers digital services to Commonwealth agencies and "
        "operates two leased datacentres in the Australian Capital Territory. "
        "The lease for both facilities expires on 30 June 2027 and will not be "
        "renewed. DDT therefore seeks a suitably qualified vendor to migrate "
        "its hosted workloads to Microsoft Azure and to provide ongoing "
        "managed platform services."
    )
    pdf.body(
        "DDT's current environment comprises approximately 580 virtual "
        "machines (predominantly Windows Server 2012 R2 and 2016, with a "
        "small Red Hat Enterprise Linux estate), 36 Microsoft SQL Server "
        "instances, and approximately 410 TB of stored data. Workloads "
        "include citizen-facing digital services classified as Tier-1, "
        "internal corporate systems, and several legacy applications "
        "earmarked for modernisation."
    )
    pdf.body(
        "This RFP sets out the mandatory and desirable requirements against "
        "which proposals will be evaluated. Respondents must address every "
        "mandatory requirement individually, providing verifiable evidence "
        "for each claim made. Unsupported claims will be disregarded by the "
        "evaluation panel."
    )

    pdf.h1("2. Definitions")
    pdf.body(
        "'Agency' means the Department of Digital Transformation. 'ISM' "
        "means the Australian Government Information Security Manual. 'IRAP' "
        "means the Infosec Registered Assessors Program. 'Tier-1 workload' "
        "means a production workload designated business-critical by the "
        "Agency. 'MTTR' means mean time to recovery for Priority 1 "
        "incidents. 'IPP' means the Commonwealth Indigenous Procurement "
        "Policy. 'Cutover window' means the agreed period during which a "
        "workload group is transitioned to the target platform."
    )

    # ── 3. Scope ─────────────────────────────────────────────────────────
    pdf.h1("3. Scope of Services")
    pdf.body(
        "The scope of this procurement comprises: (a) discovery, dependency "
        "mapping, and wave planning for all in-scope workloads; (b) design "
        "and build of an Azure landing zone compliant with the ISM at the "
        "PROTECTED level; (c) migration of all in-scope workloads to Azure; "
        "(d) modernisation of nominated application workloads, including "
        "containerisation where assessed as suitable; (e) managed platform "
        "and security operations services for an initial term of three "
        "years; and (f) full decommissioning support for both existing "
        "datacentres prior to lease expiry."
    )

    # ── 4. Mandatory Technical Requirements ─────────────────────────────
    pdf.add_page()
    pdf.h1("4. Mandatory Technical Requirements")
    pdf.body(
        "Each requirement below is mandatory unless marked otherwise. "
        "Responses must address each requirement under its reference number, "
        "citing verifiable evidence (project references, certifications, "
        "audited reports, or named personnel) for every claim."
    )
    pdf.clause(
        "MR-1 - Migration track record", "Mandatory, High priority",
        "The vendor must demonstrate proven experience migrating Windows "
        "Server 2012/2016 workloads to Azure IaaS and PaaS services, with a "
        "minimum of three completed migrations of comparable scale (500 or "
        "more virtual machines each), evidenced by contactable client "
        "references for each migration cited.",
    )
    pdf.clause(
        "MR-2 - Service levels and recovery", "Mandatory, High priority",
        "The proposed managed service must achieve a 99.95% availability SLA "
        "for Tier-1 production workloads, with continuous monitoring "
        "tooling, documented incident response procedures, and a mean time "
        "to recovery (MTTR) under 30 minutes for Priority 1 incidents. "
        "Respondents must evidence actual achieved availability and MTTR "
        "figures from current or recent operations.",
    )
    pdf.clause(
        "MR-3 - Data sovereignty and security accreditation",
        "Mandatory, High priority",
        "All Agency data must remain within Australian Azure regions "
        "(Australia East and Australia Southeast) at all times, including "
        "backup and disaster recovery copies. The vendor must hold current "
        "ISO/IEC 27001 certification covering its cloud delivery operations, "
        "and must evidence an IRAP assessment of its proposed platform "
        "architecture at the PROTECTED level under the ISM.",
    )
    pdf.clause(
        "MR-4 - Migration execution", "Mandatory, High priority",
        "The vendor must provide a zero-downtime migration approach using "
        "Azure Site Recovery or an equivalent replication-based mechanism, "
        "including rehearsal cutovers and tested rollback plans. Production "
        "cutover windows must not exceed four hours per workload group. "
        "Respondents must evidence prior cutovers completed within "
        "equivalent windows, including any data loss incidents.",
    )
    pdf.clause(
        "MR-5 - Application modernisation capability",
        "Mandatory, Medium priority",
        "The vendor must demonstrate an established application "
        "modernisation capability, including production experience "
        "designing, deploying, and operating containerised workloads on "
        "Azure Kubernetes Service (AKS) at scale, and must provide a "
        "modernisation roadmap approach for the Agency's nominated legacy "
        "applications.",
    )

    # ── 5. Commercial Requirements ───────────────────────────────────────
    pdf.add_page()
    pdf.h1("5. Mandatory Commercial Requirements")
    pdf.clause(
        "MR-6 - Pricing structure", "Mandatory, High priority",
        "Pricing must be submitted as a fixed-price schedule for Years 1, 2, "
        "and 3 of the engagement, with annual escalation capped at CPI plus "
        "2%, inclusive of all licences, migration tooling, professional "
        "services, and transition costs. Respondents should evidence prior "
        "acceptance of equivalent fixed-price structures.",
    )
    pdf.clause(
        "MR-7 - Payment terms", "Mandatory, Medium priority",
        "A milestone-based payment schedule must be provided, with each "
        "milestone's completion certified by the DDT Project Director prior "
        "to invoicing, and payment terms of net 30 days from receipt of a "
        "correctly rendered invoice.",
    )

    # ── 6. Team and Governance ───────────────────────────────────────────
    pdf.h1("6. Mandatory Team and Governance Requirements")
    pdf.clause(
        "MR-8 - Key personnel", "Mandatory, High priority",
        "The proposed delivery team must include a named Project Manager "
        "holding a current PMP or PRINCE2 Practitioner certification with a "
        "minimum of seven years of cloud migration programme experience, "
        "evidenced by a curriculum vitae. Substitution of key personnel "
        "requires the Agency's prior written approval. The vendor must also "
        "name a lead cloud architect holding current Microsoft Azure "
        "architecture certification.",
    )
    pdf.clause(
        "MR-9 - Governance cadence", "Mandatory, Low priority",
        "The vendor must operate a monthly steering committee with Agency "
        "executives and provide fortnightly written progress reports "
        "covering schedule, risk, and financial status.",
    )

    # ── 7. Legal and Compliance ──────────────────────────────────────────
    pdf.add_page()
    pdf.h1("7. Mandatory Legal and Compliance Requirements")
    pdf.clause(
        "MR-10 - Privacy and breach notification", "Mandatory, High priority",
        "The vendor must comply with the Privacy Act 1988 (Cth), the "
        "Australian Privacy Principles, and the Notifiable Data Breaches "
        "scheme. Any eligible or suspected data breach affecting Agency data "
        "must be notified to the Agency within 24 hours of discovery. "
        "Respondents must evidence their privacy management framework and "
        "tested breach response procedures.",
    )
    pdf.clause(
        "MR-11 - Indigenous Procurement Policy participation",
        "Mandatory, Medium priority",
        "Consistent with the Commonwealth Indigenous Procurement Policy, a "
        "minimum of 10% of the total contract value must be delivered "
        "through registered Indigenous businesses as subcontractors or "
        "suppliers. Respondents must identify the Indigenous businesses "
        "they propose to engage, the scope each will deliver, and any "
        "existing partnership history.",
    )
    pdf.clause(
        "MR-12 - Cryptographic agility", "Mandatory, Medium priority",
        "Recognising forthcoming Australian Signals Directorate guidance on "
        "post-quantum cryptography, the vendor must provide a quantum-safe "
        "cryptography transition plan describing how platform cryptography "
        "(data in transit, data at rest, and key management) will migrate "
        "to post-quantum algorithms by 2030, including interim "
        "crypto-agility measures.",
    )

    # ── 8. Desirable Requirements ────────────────────────────────────────
    pdf.h1("8. Desirable Requirements")
    pdf.clause(
        "DR-1 - Sustainability reporting", "Desirable",
        "Quarterly reporting of the carbon footprint attributable to the "
        "Agency's Azure consumption, with year-on-year reduction targets.",
    )
    pdf.clause(
        "DR-2 - Cost optimisation", "Desirable",
        "An ongoing FinOps practice with quarterly optimisation reviews and "
        "a shared-savings mechanism for realised cost reductions.",
    )

    # ── 9. Evaluation ────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("9. Evaluation Criteria")
    pdf.body(
        "Proposals that fail to address any mandatory requirement will be "
        "excluded from further evaluation. Compliant proposals will be "
        "scored as follows: Technical capability and migration approach - "
        "40%; Price and commercial terms - 30%; Team experience and "
        "governance - 20%; Risk management and compliance - 10%. Proposals "
        "scoring below 60% overall will not proceed to the negotiation "
        "stage. The Agency may seek clarification, conduct reference "
        "checks, and require presentations from shortlisted respondents."
    )

    pdf.h1("10. Submission Instructions")
    pdf.body(
        "Proposals must be lodged via the AusTender portal no later than "
        "17:00 AEST on 30 June 2026. Late submissions will not be accepted "
        "under any circumstances. Proposals must be submitted as a single "
        "PDF of no more than 60 pages, structured to address each "
        "requirement reference (MR-1 through MR-12, DR-1 and DR-2) in "
        "order. Questions must be lodged through the AusTender forum no "
        "later than 20 June 2026; answers will be published to all "
        "registered respondents."
    )

    pdf.h1("11. Conditions of Tender")
    pdf.body(
        "The Agency is not bound to accept the lowest-priced or any "
        "proposal. The Agency may discontinue this process at any time. "
        "Respondents bear their own costs of participation. Proposals must "
        "remain valid for 120 days from the submission deadline. The "
        "successful respondent will be required to enter into the "
        "Commonwealth contract attached as Annex C (not reproduced in this "
        "demonstration document), including provisions for liquidated "
        "damages, key personnel, and step-in rights."
    )

    # ── Appendix ─────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("Appendix A - Current Environment Summary")
    pdf.body(
        "Virtual machines: approximately 580 (430 Windows Server 2012 "
        "R2/2016, 95 Windows Server 2019, 55 RHEL 8). Databases: 36 SQL "
        "Server instances (2014-2019), total 48 TB. Storage: approximately "
        "410 TB across SAN and NAS tiers. Network: dual 10 Gbps links "
        "between datacentres; ExpressRoute not yet provisioned. Identity: "
        "Active Directory (2016 functional level) with Entra ID Connect "
        "synchronisation already in place. Backup: nightly full to disk "
        "with 35-day retention; quarterly archive to tape."
    )
    pdf.h2("Workload tiers")
    pdf.body(
        "Tier-1 (24 applications): citizen-facing digital services and "
        "payment systems; 99.95% availability required; cutover windows "
        "strictly limited to four hours. Tier-2 (61 applications): internal "
        "corporate and case-management systems. Tier-3: development, test, "
        "and archive workloads. Legacy modernisation candidates: 8 "
        "applications nominated for containerisation or re-platforming "
        "assessment during the engagement."
    )

    pdf.add_page()
    pdf.h1("Appendix B - Indicative Timeline and Risk Allocation")
    pdf.h2("Indicative programme timeline")
    pdf.body(
        "Contract execution: August 2026. Discovery and landing zone build: "
        "August - November 2026. Migration waves: December 2026 - March "
        "2027. Modernisation assessments: from January 2027. Datacentre "
        "decommissioning and lease exit: complete by 30 June 2027. Managed "
        "services steady state: from April 2027 for the remainder of the "
        "three-year term. Respondents may propose an alternative timeline "
        "provided the lease-exit date is met."
    )
    pdf.h2("Risk allocation principles")
    pdf.body(
        "The vendor bears delivery risk for migration execution, including "
        "rollback costs arising from failed cutovers. The Agency bears risk "
        "for delays caused by Agency-side approvals exceeding agreed "
        "turnaround times. Liquidated damages apply to missed lease-exit "
        "milestones attributable to the vendor. Caps on liability will be "
        "negotiated with the preferred respondent within Commonwealth "
        "contracting norms; unlimited liability applies for breach of "
        "privacy or security obligations."
    )
    pdf.h2("Glossary of evaluation terms")
    pdf.body(
        "'Compliant' means the proposal fully addresses the requirement "
        "with verifiable evidence. 'Partially compliant' means the proposal "
        "addresses the requirement but evidence is incomplete or the "
        "capability is not yet demonstrated at the required scale. "
        "'Non-compliant' means the requirement is not addressed or no "
        "evidence is provided. Mandatory requirements assessed as "
        "non-compliant result in exclusion; partial compliance on mandatory "
        "requirements must be justified with a credible remediation plan."
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT))
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    build()
