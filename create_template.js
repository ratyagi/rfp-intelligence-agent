const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, BorderStyle, WidthType, ShadingType,
  HeadingLevel, PageNumber, PageBreak,
} = require('docx');
const fs = require('fs');

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const cellBorders = { top: border, bottom: border, left: border, right: border };
const headerColor = "1F4E79";  // dark blue

function makeHeaderRow(cols, widths) {
  return new TableRow({
    children: cols.map((text, i) => new TableCell({
      borders: cellBorders,
      width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: headerColor, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({
        children: [new TextRun({ text, bold: true, color: "FFFFFF", font: "Arial", size: 20 })]
      })]
    }))
  });
}

function makeDataRow(cells, widths, isGap = false) {
  return new TableRow({
    children: cells.map((text, i) => new TableCell({
      borders: cellBorders,
      width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: isGap ? "FFE0E0" : "FFFFFF", type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({
        children: [new TextRun({
          text,
          color: isGap ? "CC0000" : "000000",
          font: "Arial",
          size: 18,
        })]
      })]
    }))
  });
}

const colWidths = [1500, 4500, 3360];  // sum = 9360

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: "Arial", size: 22 } }
    },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: "1F4E79" },
        paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 }
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "2E75B6" },
        paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 1 }
      },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 1 } },
          children: [new TextRun({ text: "RFP Intelligence Agent — Proposal Draft", font: "Arial", size: 18, color: "2E75B6" })]
        })]
      })
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "CONFIDENTIAL — DRAFT — Requires human review before submission", font: "Arial", size: 16, color: "CC0000", bold: true }),
          ]
        })]
      })
    },
    children: [
      // ── COVER PAGE ────────────────────────────────────────────────────────
      new Paragraph({ spacing: { before: 2880 }, children: [] }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "{{company_name}}", font: "Arial", size: 52, bold: true, color: "1F4E79" })]
      }),
      new Paragraph({ spacing: { before: 240 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Proposal in Response to:", font: "Arial", size: 24, color: "595959" })]
      }),
      new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "{{rfp_title}}", font: "Arial", size: 36, bold: true, color: "2E75B6" })]
      }),
      new Paragraph({ spacing: { before: 480 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Submitted: {{submission_date}}", font: "Arial", size: 24, color: "595959" })]
      }),

      // ── PAGE BREAK ────────────────────────────────────────────────────────
      new Paragraph({ children: [new PageBreak()] }),

      // ── EXECUTIVE SUMMARY ─────────────────────────────────────────────────
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("1. Executive Summary")] }),
      new Paragraph({
        spacing: { before: 120, after: 240 },
        children: [new TextRun({ text: "{{executive_summary}}", font: "Arial", size: 22 })]
      }),

      // ── REQUIREMENTS RESPONSE TABLE ───────────────────────────────────────
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("2. Requirements Response")] }),
      new Paragraph({
        spacing: { before: 80, after: 160 },
        children: [new TextRun({ text: "The table below addresses each requirement from the RFP. Rows highlighted in red require action before submission.", font: "Arial", size: 20, color: "595959" })]
      }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: colWidths,
        rows: [
          makeHeaderRow(["Req ID", "Our Response", "Supporting Evidence"], colWidths),
          makeDataRow(["{{req_id}}", "{{response_text}}", "{{evidence_citations}}"], colWidths, false),
          makeDataRow(["{{req_id_gap}}", "[ACTION REQUIRED: {{gap_description}}]", "No evidence on file"], colWidths, true),
        ]
      }),

      // ── GAP SUMMARY ───────────────────────────────────────────────────────
      new Paragraph({ spacing: { before: 480 }, heading: HeadingLevel.HEADING_1, children: [new TextRun("3. Gap Summary")] }),
      new Paragraph({
        spacing: { before: 80, after: 120 },
        children: [new TextRun({ text: "{{gap_summary}}", font: "Arial", size: 22 })]
      }),

      // ── WIN PROBABILITY ───────────────────────────────────────────────────
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("4. Estimated Fit Score")] }),
      new Paragraph({
        spacing: { before: 80 },
        children: [
          new TextRun({ text: "Estimated fit score: ", font: "Arial", size: 24 }),
          new TextRun({ text: "{{win_probability}}%", font: "Arial", size: 24, bold: true, color: "1F4E79" }),
        ]
      }),
      new Paragraph({
        spacing: { before: 40 },
        children: [new TextRun({ text: "Score reflects coverage of requirements by verified internal evidence. All gaps must be resolved before submission.", font: "Arial", size: 18, color: "595959" })]
      }),
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("templates/proposal_template.docx", buf);
  console.log("Template created: templates/proposal_template.docx");
});
