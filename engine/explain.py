"""Transparent explanations: every decision is traceable to a rule and a student input."""
from __future__ import annotations
from .eligibility import ConditionResult, EvaluationResult
from .logic import Tri

COND_FIELDS = ["student_input", "requirement", "logical_rule", "result", "evidence", "explanation"]
SYMBOL = {"TRUE": "[TRUE]", "FALSE": "[FALSE]", "UNKNOWN": "[UNKNOWN]"}


def _flatten(conds):
    for c in conds:
        yield c
        yield from _flatten(c.children)


def explain_condition(c: ConditionResult) -> dict:
    return {"student_input": c.student_value, "requirement": c.required, "logical_rule": c.rule,
            "result": c.result.value, "evidence": c.evidence, "explanation": c.explanation,
            "missing_information": c.missing_info or ("None" if c.result is not Tri.UNKNOWN else ""),
            "label": c.label, "gap": c.gap_text}


def explain_result(r: EvaluationResult) -> dict:
    return {
        "programme": r.programme_name, "rule_expression": r.rule_expression,
        "rule_version": r.rule_version, "source": r.source,
        "conditions": [explain_condition(c) for c in r.conditions],
        "missing_information": r.missing_information,
        "final_decision": r.decision, "final_explanation": r.final_explanation,
        "notice": "Sample criteria are illustrative and not official admission requirements."
                  if (r.source or {}).get("verification_status") != "Verified" else
                  "Criteria marked Verified; confirm with the institution before acting.",
    }


def explanation_completeness(r: EvaluationResult) -> tuple:
    """Return (score 0..1, list of missing items). Each required field of each condition counts once."""
    total, present, gaps = 0, 0, []
    for c in _flatten(r.conditions):
        d = explain_condition(c)
        needed = list(COND_FIELDS) + (["missing_information"] if c.result is Tri.UNKNOWN else [])
        for f in needed:
            total += 1
            if str(d.get(f, "")).strip():
                present += 1
            else:
                gaps.append(f"{c.req_id}.{f}")
    for name, val in (("final_decision", r.decision), ("final_explanation", r.final_explanation),
                      ("rule_expression", r.rule_expression)):
        total += 1
        if str(val).strip():
            present += 1
        else:
            gaps.append(name)
    return (present / total if total else 1.0), gaps


def explanation_markdown(r: EvaluationResult) -> str:
    e = explain_result(r)
    lines = [f"### {e['programme']}", f"**Rule:** `{e['rule_expression']}`", ""]
    for c in e["conditions"]:
        lines += [f"- **{c['label']}** - student: {c['student_input']}; required: {c['requirement']}; "
                  f"rule `{c['logical_rule']}` -> {SYMBOL[c['result']]}", f"  - {c['explanation']}"]
    lines += ["", f"**Final decision:** {e['final_decision']}", e["final_explanation"], f"_{e['notice']}_"]
    return "\n".join(lines)
