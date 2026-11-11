"""CSV / PDF report builders (reportlab). PDFs use built-in fonts, so text is sanitised to Latin-1."""
from __future__ import annotations
import io
from datetime import datetime
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .constants import REPORTS_DIR

DISCLAIMER = ("Sample admission criteria in this system are illustrative and are NOT official university requirements. "
              "Decisions come from deterministic rules; no probabilities or AI models are used.")


def _clean(text) -> str:
    s = "" if text is None else str(text)
    s = s.replace("\u2192", "->").replace("\u2265", ">=").replace("\u2264", "<=").replace("\u2013", "-").replace("\u2014", "-")
    return s.encode("latin-1", "replace").decode("latin-1")


def results_dataframe(results: list) -> pd.DataFrame:
    return pd.DataFrame([{"Programme": r.programme_name, "Level": r.level, "Field": r.field, "Decision": r.decision,
                          "Passed": len(r.passed), "Failed": len(r.failed), "Unknown": len(r.unknown),
                          "Rule version": r.rule_version,
                          "Source status": (r.source or {}).get("verification_status", "Unverified")} for r in results])


def conditions_dataframe(results: list) -> pd.DataFrame:
    rows = []
    for r in results:
        for c in r.conditions:
            rows.append({"Programme": r.programme_name, "Condition": c.label, "Rule": c.rule, "Student input": c.student_value,
                         "Required": c.required, "Result": c.result.value, "Gap": c.gap_text, "Evidence": c.evidence,
                         "Explanation": c.explanation, "Missing information": c.missing_info or "",
                         "Programme decision": r.decision})
    return pd.DataFrame(rows)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def build_pdf(title: str, subtitle: str, sections: list) -> bytes:
    """sections: [{'heading': str, 'paragraphs': [str], 'table': {'header': [..], 'rows': [[..]]}}]"""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
                            title=_clean(title))
    st = getSampleStyleSheet()
    small = st["BodyText"].clone("small", fontSize=8, leading=10)
    story = [Paragraph(escape(_clean(title)), st["Title"]), Paragraph(escape(_clean(subtitle)), st["Normal"]), Spacer(1, 4 * mm),
             Paragraph(escape(_clean(DISCLAIMER)), small), Spacer(1, 4 * mm)]
    width = A4[0] - 30 * mm
    for sec in sections:
        story.append(Paragraph(escape(_clean(sec["heading"])), st["Heading2"]))
        for para in sec.get("paragraphs", []):
            story.append(Paragraph(escape(_clean(para)), st["BodyText"]))
        tbl = sec.get("table")
        if tbl and tbl["rows"]:
            data = [[Paragraph(f"<b>{escape(_clean(h))}</b>", small) for h in tbl["header"]]]
            data += [[Paragraph(escape(_clean(c)), small) for c in row] for row in tbl["rows"]]
            t = Table(data, colWidths=[width / len(tbl["header"])] * len(tbl["header"]), repeatRows=1)
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef7")),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story += [Spacer(1, 2 * mm), t]
        story.append(Spacer(1, 4 * mm))
    doc.build(story)
    return buf.getvalue()


def _profile_lines(p: dict) -> list:
    f = lambda v: "not provided" if v in (None, "") else v
    return [f"Student: {f(p.get('name'))} ({p.get('student_id')})", f"Stream: {f(p.get('stream'))}",
            f"Class 10: {f(p.get('class10_pct'))}%   Class 12: {f(p.get('class12_pct'))}%   Overall: {f(p.get('overall_pct'))}%",
            "Marks: " + ", ".join(f"{k.replace('_', ' ')} {f(v)}" for k, v in p.get("marks", {}).items())]


def evaluation_pdf(profile: dict, results: list) -> bytes:
    sections = [{"heading": "Student profile", "paragraphs": _profile_lines(profile)},
                {"heading": "Eligibility summary",
                 "table": {"header": ["Programme", "Level", "Decision", "Passed", "Failed", "Unknown"],
                           "rows": [[r.programme_name, r.level, r.decision, len(r.passed), len(r.failed), len(r.unknown)] for r in results]}}]
    for r in results:
        sections.append({"heading": f"{r.programme_name}: {r.decision}",
                         "paragraphs": [f"Rule: {r.rule_expression}", r.final_explanation],
                         "table": {"header": ["Condition", "Student", "Required", "Result", "Gap"],
                                   "rows": [[c.label, c.student_value, c.required, c.result.value, c.gap_text] for c in r.conditions]}})
    return build_pdf("Academic Eligibility Report", datetime.now().strftime("Generated %Y-%m-%d %H:%M"), sections)


def gap_pdf(profile: dict, analysis: dict) -> bytes:
    sections = [{"heading": "Student profile", "paragraphs": _profile_lines(profile)},
                {"heading": f"Marks-gap analysis: {analysis['programme']} ({analysis['decision']})",
                 "paragraphs": [analysis["summary"]],
                 "table": {"header": ["Condition", "Student", "Required", "Gap", "Status"],
                           "rows": [[r["Condition"], r["Student marks"], r["Required"], r["Gap"], r["Status"]] for r in analysis["rows"]]}},
                {"heading": "Information required", "paragraphs": analysis["information_required"] or ["None"]},
                {"heading": "Possible next steps", "paragraphs": analysis["next_steps"] or ["None - all conditions satisfied."]}]
    return build_pdf("Missing Conditions Report", datetime.now().strftime("Generated %Y-%m-%d %H:%M"), sections)


def roadmap_pdf(profile: dict, roadmap: dict) -> bytes:
    sections = [{"heading": "Student profile", "paragraphs": _profile_lines(profile)},
                {"heading": f"Roadmap to {roadmap['target']}",
                 "paragraphs": [f"Progress: {roadmap['done']} of {roadmap['total']} items done. Current decision: {roadmap['decision']}.",
                                roadmap["note"]]}]
    for s in roadmap["stages"]:
        rows = [["[x]" if i["done"] else "[ ]", i["text"], i.get("detail", "")] for i in s["items"]]
        sections.append({"heading": f"{s['stage']}. {s['title']}", "paragraphs": [] if rows else [s.get("empty") or s.get("explanation", "")],
                         "table": {"header": ["Done", "Item", "Detail"], "rows": rows}})
    return build_pdf("Academic Improvement Roadmap", datetime.now().strftime("Generated %Y-%m-%d %H:%M"), sections)


def save_report(data: bytes, filename: str, directory: Optional[Path] = None) -> str:
    d = Path(directory or REPORTS_DIR)
    d.mkdir(parents=True, exist_ok=True)
    path = d / filename
    path.write_bytes(data)
    return str(path)
