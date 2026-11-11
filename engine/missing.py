"""Missing-conditions and marks-gap analysis."""
from __future__ import annotations
from .eligibility import ConditionResult, EvaluationResult
from .logic import Tri, fmt

STATUS_ICON = {Tri.TRUE: "Passed", Tri.FALSE: "Failed", Tri.UNKNOWN: "Unknown"}


def gap_rows(result: EvaluationResult) -> list:
    rows = []
    for c in result.conditions:
        rows.append({"Condition": c.label, "Student marks": c.student_value, "Required": c.required,
                     "Gap": c.gap_text, "Status": STATUS_ICON[c.result], "Rule": c.rule,
                     "Why": c.explanation})
    return rows


def next_steps(c: ConditionResult) -> list:
    """Deterministic, non-promissory suggestions for one FALSE / UNKNOWN condition."""
    m, kind = c.meta, c.meta.get("kind")
    if c.result is Tri.UNKNOWN:
        return [f"Provide: {c.missing_info or c.label}. Update your Student Profile and re-run the evaluation."]
    steps = []
    if c.rtype in ("min_overall", "min_class10") or (kind == "numeric" and not m.get("not_studied")):
        steps.append(f"You are {c.gap_text} short on '{c.label}'. Recorded marks change only through an official "
                     "re-assessment or an improvement / supplementary examination, if your board allows it.")
        if m.get("subject") not in (None, "overall", "class10"):
            steps.append("Courses can build knowledge in this subject (see Certificate Planner) but they do not change "
                         "recorded marks or formal eligibility.")
    elif m.get("not_studied") or c.rtype == "subject_studied":
        steps.append("This subject was not studied. Look for foundation or bridge routes and ask the institution whether "
                     "it accepts a bridge course (see Alternative Pathways).")
    elif c.rtype == "stream_in":
        steps.append(f"Your stream is not accepted here ({c.required}). Explore programmes and routes that accept your stream.")
    elif c.rtype == "entrance":
        steps.append(f"Check the official notification for {c.required.replace('Qualified in ', '')}: eligibility, dates and "
                     "registration. Update your profile after the result.")
    elif c.rtype == "qualification":
        steps.append(f"Requirement not met: {c.label}. Check which prior qualification or discipline the programme accepts.")
    elif c.rtype == "certificate":
        steps.append(f"This sample rule names the following accepted certificate(s): {c.required}. Confirm acceptance with the real institution.")
    elif c.rtype == "any_of":
        steps.append("Satisfy at least one alternative: " + c.rule)
    else:
        steps.append(f"Requirement not met: {c.label}.")
    return steps


def analyse(result: EvaluationResult) -> dict:
    steps = []
    for c in result.failed + result.unknown:
        steps.extend(next_steps(c))
    numeric_gaps = [(c.label, c.gap) for c in result.failed if c.gap is not None]
    return {
        "programme": result.programme_name, "decision": result.decision,
        "passed": result.passed, "failed": result.failed, "unknown": result.unknown,
        "rows": gap_rows(result),
        "information_required": [c.missing_info for c in result.unknown if c.missing_info],
        "next_steps": steps, "numeric_gaps": numeric_gaps,
        "total_numeric_gap": round(sum(g for _, g in numeric_gaps), 6),
        "summary": result.final_explanation,
    }
