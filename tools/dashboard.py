"""Self-contained HTML dashboard — the human-facing view of a pipeline run.

A single static .html file (no server, no external assets, no network) generated
from the same data as the Bid Decision Report. It is the demo's hero screen:
coverage score, the six-stage pipeline, the citation-verification result, and a
per-requirement breakdown with green/amber/red status.

Security: every piece of model-generated text (requirement text, drafted
responses, titles, gap notes) is HTML-escaped before it reaches the page, so
nothing in the output can inject markup or script.
"""
from html import escape
from pathlib import Path

_SCORE_META = {
    "COVERED": ("Covered", "covered"),
    "PARTIAL": ("Partial", "partial"),
    "GAP": ("Action required", "gap"),
}

_STAGES = [
    ("1", "Intake", "gpt-4.1", "llm", "Extracts every requirement from the RFP"),
    ("2", "Research", "Foundry IQ", "det", "Retrieves cited evidence per requirement"),
    ("3", "Scorer", "gpt-4.1", "llm", "Judges COVERED / PARTIAL / GAP"),
    ("4", "Drafter", "gpt-4.1", "llm", "Writes responses, citing only retrieved docs"),
    ("5", "Verifier", "deterministic", "det", "Strips any citation that does not resolve"),
    ("6", "Review", "deterministic", "det", "Builds the proposal, report and this view"),
]


def build_dashboard(verified_draft: dict, report: dict, output_path: str) -> str:
    """Render the run as a static HTML dashboard. Returns the absolute path."""
    counts = report.get("counts", {})
    citations = report.get("citations", {})
    coverage = report.get("coverage_score", 0) or 0
    recommendation = report.get("recommendation", "")
    rationale = report.get("recommendation_rationale", "")
    rfp_title = verified_draft.get("rfp_title", "RFP Response")
    company = verified_draft.get("company_name", "")
    submission_date = verified_draft.get("submission_date", "")
    exec_summary = verified_draft.get("executive_summary", "")

    total = counts.get("total", 0) or 1
    cov_n = counts.get("covered", 0)
    par_n = counts.get("partial", 0)
    gap_n = counts.get("gap", 0)
    cit_total = citations.get("total", 0)
    cit_verified = citations.get("verified", 0)
    cit_stripped = citations.get("stripped", 0)

    band = "covered" if coverage >= 70 else ("partial" if coverage >= 50 else "gap")

    stages_html = "".join(
        f"""
        <div class="stage {kind}">
          <div class="stage-top"><span class="stage-num">{escape(num)}</span>
            <span class="stage-tag {kind}">{'LLM' if kind == 'llm' else 'CODE'}</span></div>
          <div class="stage-name">{escape(name)}</div>
          <div class="stage-engine">{escape(engine)}</div>
          <div class="stage-desc">{escape(desc)}</div>
        </div>"""
        for num, name, engine, kind, desc in _STAGES
    )

    rows_html = "".join(_row(req) for req in verified_draft.get("requirements", []))

    # Coverage bar segments (covered + partial + gap), widths as percentages.
    seg = lambda n: round(n / total * 100, 1)
    cov_w, par_w, gap_w = seg(cov_n), seg(par_n), seg(gap_n)

    stripped_line = (
        f"{cit_stripped} stripped by the Verifier" if cit_stripped
        else "0 stripped — every citation resolved"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RFP Intelligence Agent — {escape(rfp_title)}</title>
<style>
  :root {{
    --bg:#f3f4f6; --card:#ffffff; --ink:#1b1a19; --muted:#605e5c; --line:#e1dfdd;
    --blue:#0f6cbd; --blue-deep:#115ea3; --green:#0e7038; --green-bg:#e6f4ea;
    --amber:#8a6100; --amber-bg:#fdf3e0; --red:#b10e1c; --red-bg:#fde7e9;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font-family:'Segoe UI',system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:32px 24px 64px; }}
  header.top {{ display:flex; justify-content:space-between; align-items:flex-start;
    gap:24px; flex-wrap:wrap; border-bottom:3px solid var(--blue); padding-bottom:20px; }}
  .brand {{ font-size:13px; font-weight:600; letter-spacing:.08em; text-transform:uppercase;
    color:var(--blue); }}
  h1 {{ font-size:26px; margin:6px 0 4px; line-height:1.25; }}
  .sub {{ color:var(--muted); font-size:14px; }}
  .run-meta {{ text-align:right; font-size:12.5px; color:var(--muted); line-height:1.7; }}
  .run-meta b {{ color:var(--ink); }}
  .pill {{ display:inline-block; padding:2px 9px; border-radius:999px; font-size:11px;
    font-weight:600; }}
  .pill.foundry {{ background:#e7f0fb; color:var(--blue-deep); }}

  .hero {{ display:grid; grid-template-columns:1.1fr 1fr 1fr; gap:16px; margin:24px 0; }}
  .metric {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:20px 22px; }}
  .metric .label {{ font-size:12px; color:var(--muted); text-transform:uppercase;
    letter-spacing:.06em; font-weight:600; }}
  .score-num {{ font-size:52px; font-weight:700; line-height:1; margin-top:6px; }}
  .score-num.covered {{ color:var(--green); }} .score-num.partial {{ color:var(--amber); }}
  .score-num.gap {{ color:var(--red); }}
  .score-note {{ font-size:12px; color:var(--muted); margin-top:8px; }}
  .rec {{ display:inline-block; margin-top:10px; padding:6px 12px; border-radius:8px;
    font-weight:700; font-size:14px; }}
  .rec.covered {{ background:var(--green-bg); color:var(--green); }}
  .rec.partial {{ background:var(--amber-bg); color:var(--amber); }}
  .rec.gap {{ background:var(--red-bg); color:var(--red); }}
  .verif {{ display:flex; align-items:center; gap:12px; margin-top:8px; }}
  .verif .big {{ font-size:40px; font-weight:700; color:var(--green); line-height:1; }}
  .check {{ width:30px; height:30px; border-radius:50%; background:var(--green);
    color:#fff; display:flex; align-items:center; justify-content:center; font-size:18px; }}

  .barwrap {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:18px 22px; margin-bottom:24px; }}
  .bar {{ display:flex; height:22px; border-radius:6px; overflow:hidden; margin-top:10px;
    border:1px solid var(--line); }}
  .bar i {{ display:block; height:100%; }}
  .bar .c {{ background:var(--green); }} .bar .p {{ background:#e8a13a; }}
  .bar .g {{ background:#d3434f; }}
  .legend {{ display:flex; gap:20px; margin-top:12px; font-size:13px; color:var(--muted);
    flex-wrap:wrap; }}
  .legend span b {{ color:var(--ink); }}
  .dot {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; }}

  h2 {{ font-size:15px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted);
    margin:28px 0 12px; }}
  .pipeline {{ display:grid; grid-template-columns:repeat(6,1fr); gap:10px; }}
  .stage {{ background:var(--card); border:1px solid var(--line); border-top:3px solid var(--blue);
    border-radius:10px; padding:12px; }}
  .stage.det {{ border-top-color:#8a8886; }}
  .stage-top {{ display:flex; justify-content:space-between; align-items:center; }}
  .stage-num {{ font-size:18px; font-weight:700; color:var(--muted); }}
  .stage-tag {{ font-size:9px; font-weight:700; padding:2px 6px; border-radius:4px;
    letter-spacing:.05em; }}
  .stage-tag.llm {{ background:#e7f0fb; color:var(--blue-deep); }}
  .stage-tag.det {{ background:#eceae9; color:#3b3a39; }}
  .stage-name {{ font-weight:600; margin-top:8px; }}
  .stage-engine {{ font-size:11px; color:var(--blue-deep); font-weight:600; }}
  .stage-desc {{ font-size:11px; color:var(--muted); margin-top:6px; line-height:1.4; }}

  .summary {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:18px 22px; font-size:14px; line-height:1.6; color:#33312f; }}

  table {{ width:100%; border-collapse:collapse; background:var(--card);
    border:1px solid var(--line); border-radius:12px; overflow:hidden; font-size:13.5px; }}
  th {{ text-align:left; background:#faf9f8; color:var(--muted); font-size:11px;
    text-transform:uppercase; letter-spacing:.05em; padding:11px 14px; border-bottom:1px solid var(--line); }}
  td {{ padding:12px 14px; border-bottom:1px solid var(--line); vertical-align:top; }}
  tr:last-child td {{ border-bottom:none; }}
  .req-id {{ font-weight:700; white-space:nowrap; }}
  .chips {{ margin-top:5px; }}
  .chip {{ font-size:10.5px; color:var(--muted); background:#f3f2f1; border-radius:4px;
    padding:1px 6px; margin-right:4px; }}
  .badge {{ font-weight:700; font-size:12px; padding:3px 10px; border-radius:6px; white-space:nowrap; }}
  .badge.covered {{ background:var(--green-bg); color:var(--green); }}
  .badge.partial {{ background:var(--amber-bg); color:var(--amber); }}
  .badge.gap {{ background:var(--red-bg); color:var(--red); }}
  .cite {{ display:inline-block; font-size:11px; font-weight:600; color:var(--green);
    background:var(--green-bg); border-radius:4px; padding:1px 7px; margin:2px 4px 0 0; }}
  .cite.stripped {{ color:var(--red); background:var(--red-bg); text-decoration:line-through; }}
  .action {{ color:var(--red); font-size:12.5px; }}
  .resp {{ color:#33312f; }}
  footer {{ margin-top:32px; padding-top:18px; border-top:1px solid var(--line);
    font-size:12px; color:var(--muted); line-height:1.6; }}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div>
      <div class="brand">RFP Intelligence Agent</div>
      <h1>{escape(rfp_title)}</h1>
      <div class="sub">{escape(company)}{' &middot; ' if company and submission_date else ''}{escape(submission_date)}</div>
    </div>
    <div class="run-meta">
      <div>Reasoning: <span class="pill foundry">Microsoft Foundry gpt-4.1</span></div>
      <div>Retrieval: <span class="pill foundry">Foundry IQ &middot; Azure AI Search</span></div>
      <div><b>{total}</b> requirements analysed</div>
    </div>
  </header>

  <section class="hero">
    <div class="metric">
      <div class="label">Requirement coverage score</div>
      <div class="score-num {band}">{coverage}%</div>
      <div class="rec {band}">{escape(recommendation)}</div>
      <div class="score-note">{escape(rationale)}</div>
    </div>
    <div class="metric">
      <div class="label">Citations verified</div>
      <div class="verif"><span class="check">&#10003;</span>
        <span class="big">{cit_verified}/{cit_total}</span></div>
      <div class="score-note">{escape(stripped_line)}. Each verified citation resolves to a document that was actually retrieved.</div>
    </div>
    <div class="metric">
      <div class="label">Outcome mix</div>
      <div class="score-num" style="font-size:34px;margin-top:10px;">{cov_n} / {par_n} / {gap_n}</div>
      <div class="score-note">Covered / Partial / Gaps flagged for human action</div>
    </div>
  </section>

  <div class="barwrap">
    <div class="label" style="font-size:12px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.06em;">Requirement outcomes</div>
    <div class="bar">
      <i class="c" style="width:{cov_w}%"></i><i class="p" style="width:{par_w}%"></i><i class="g" style="width:{gap_w}%"></i>
    </div>
    <div class="legend">
      <span><span class="dot" style="background:var(--green)"></span><b>{cov_n}</b> Covered</span>
      <span><span class="dot" style="background:#e8a13a"></span><b>{par_n}</b> Partial</span>
      <span><span class="dot" style="background:#d3434f"></span><b>{gap_n}</b> Action required</span>
    </div>
  </div>

  <h2>The reasoning pipeline</h2>
  <div class="pipeline">{stages_html}</div>

  <h2>Executive summary</h2>
  <div class="summary">{escape(exec_summary)}</div>

  <h2>Requirement-by-requirement decisions</h2>
  <table>
    <thead><tr><th>Requirement</th><th>Decision</th><th>Evidence &amp; response</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>

  <footer>
    Generated by the RFP Intelligence Agent pipeline (Microsoft Foundry gpt-4.1 + Foundry IQ).
    Proof of concept on a synthetic RFP and a synthetic evidence corpus. The Verifier guarantees
    citation <b>provenance</b> — every shown citation resolves to a document that was retrieved for
    that requirement; claim-level fact-checking is on the roadmap. Nothing ships without human approval.
  </footer>
</div>
</body>
</html>"""

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return str(out.resolve())


def _row(req: dict) -> str:
    score = req.get("score", "GAP")
    label, cls = _SCORE_META.get(score, _SCORE_META["GAP"])
    req_text = escape((req.get("text") or "")[:240])
    priority = escape(req.get("priority", "medium"))
    category = escape(req.get("category", "other"))
    conf = req.get("confidence")
    conf_str = f"{conf:.0%}" if isinstance(conf, (int, float)) else "n/a"

    verification = req.get("verification") or {}
    verified = verification.get("verified", []) or []
    stripped = verification.get("stripped", []) or []
    cites = "".join(f'<span class="cite">{escape(c)} &#10003;</span>' for c in verified)
    cites += "".join(f'<span class="cite stripped">{escape(c)}</span>' for c in stripped)

    if score == "GAP":
        note = escape(req.get("gap_note") or "No internal evidence found for this requirement.")
        detail = f'<div class="action"><b>ACTION REQUIRED:</b> {note}</div>'
    else:
        resp = escape((req.get("response_text") or "")[:420])
        detail = f'<div class="resp">{resp}</div>'
        if cites:
            detail += f'<div class="chips" style="margin-top:8px;">{cites}</div>'

    return f"""
      <tr>
        <td><div class="req-id">{escape(req.get('id',''))}</div>
          <div>{req_text}</div>
          <div class="chips"><span class="chip">{priority}</span><span class="chip">{category}</span></div></td>
        <td><span class="badge {cls}">{label}</span>
          <div class="score-note" style="margin-top:6px;">confidence {conf_str}</div></td>
        <td>{detail}</td>
      </tr>"""
