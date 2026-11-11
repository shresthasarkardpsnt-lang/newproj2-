"""Applicant-facing view of the reasoning engine (pure Python, no Streamlit).

Adds what the applicant interface must expose on top of the unchanged eligibility rules and gap calculations:
confidence, supporting evidence, exception handling, human-review states, the reasoning chain, feasible
alternative pathways, and a baseline comparison. Nothing here changes a decision: it only describes one.

"Confidence" is a deterministic label (how completely the decision is backed by checked conditions). It is
NOT a probability and nothing is learned or estimated.
"""
from __future__ import annotations

from typing import Optional

from .constants import ELIGIBLE, ENTRANCE_PENDING, NEEDS_REVIEW, NOT_ELIGIBLE
from .eligibility import EvaluationResult, evaluate_all, evaluate_programme
from .evaluation import baseline_eligible
from .explain import explain_condition
from .kb import cert_names, prog_by_id
from .logic import Tri, to_number
from .missing import analyse
from .pathway import find_routes
from .validation import normalise_profile, validate_profile

BORDERLINE_POINTS = 2.0          # within this many points of a threshold = "borderline"
NOT_MODELLED = ("Seat quotas, category reservations, age limits, interviews and portfolios are not modelled. "
                "Always confirm with the institution.")


def _leaves(conds):
    for c in conds:
        if c.children:
            yield from _leaves(c.children)
        else:
            yield c


def _margin(c) -> Optional[float]:
    """Marks above (+) or below (-) the threshold for a numeric condition, else None."""
    if c.meta.get("kind") != "numeric" or c.meta.get("not_studied"):
        return None
    v, t = to_number(str(c.student_value).rstrip("%")), to_number(str(c.required).rstrip("%"))
    return None if v is None or t is None else round(v - t, 6)


def borderline_items(r: EvaluationResult) -> list:
    out = []
    for c in _leaves(r.conditions):
        m = _margin(c)
        if m is not None and c.result is not Tri.UNKNOWN and abs(m) <= BORDERLINE_POINTS and (m >= 0 or c.result is Tri.FALSE):
            out.append((c, m))
    return out


def completeness(r: EvaluationResult) -> float:
    n = len(r.conditions)
    return 1.0 if n == 0 else (n - len(r.unknown)) / n


def confidence(r: EvaluationResult) -> dict:
    """Deterministic confidence label with the reason behind it."""
    comp, border = completeness(r), borderline_items(r)
    if r.decision == NEEDS_REVIEW:
        return {"label": "Low", "pct": comp, "basis": f"{len(r.unknown)} condition(s) cannot be checked yet, so no definite decision is made."}
    if r.unknown:
        return {"label": "Medium", "pct": comp, "basis": "The decision is already certain (a failed condition cannot be undone), "
                                                          f"but {len(r.unknown)} other condition(s) were not checked."}
    if border:
        return {"label": "Medium", "pct": comp, "basis": f"Every condition was checked, but {len(border)} mark(s) sit within "
                                                          f"{BORDERLINE_POINTS:g} points of a threshold: re-check them."}
    return {"label": "High", "pct": comp, "basis": "Every condition was checked from the data you provided and none is borderline."}


def _pending_exams(r: EvaluationResult, profile: dict) -> list:
    exams = profile.get("entrance_exams") or {}
    out = []
    for c in _leaves(r.conditions):
        if c.result is Tri.UNKNOWN and c.meta.get("kind") == "entrance":
            out += [e for e in c.meta.get("exams", []) if (exams.get(e) or {}).get("status") in ENTRANCE_PENDING]
    return list(dict.fromkeys(out))


def review_state(r: EvaluationResult, profile: dict) -> dict:
    """Human-review state: who has to do what next for this conclusion to become final."""
    pending = _pending_exams(r, profile)
    if r.decision == NEEDS_REVIEW and pending:
        return {"code": "human", "label": "Human review required",
                "why": f"Waiting for an external result ({', '.join(pending)}). Re-run once it is declared; "
                       "an admissions officer should confirm the final outcome."}
    if r.decision == NEEDS_REVIEW:
        return {"code": "input", "label": "Needs your input",
                "why": "Add the missing details on the Profile page. No guess is made for blank fields."}
    if borderline_items(r):
        return {"code": "check", "label": "Double-check suggested",
                "why": "A mark is within 2 points of a threshold. Confirm it against your official marksheet."}
    return {"code": "auto", "label": "Decided automatically", "why": "Definite result; no human review is triggered by the rules."}


def exceptions(r: EvaluationResult, profile: dict) -> list:
    """Exception handling: every unusual condition that was handled explicitly instead of guessed."""
    out = []
    for e in _pending_exams(r, profile):
        out.append(("Pending result", f"{e}: result not declared yet, treated as UNKNOWN (never as pass or fail)."))
    for c in _leaves(r.conditions):
        if c.meta.get("not_studied"):
            out.append(("Subject not studied", f"{c.label}: the subject was not studied, so this cannot be met directly. See bridge routes."))
        elif c.result is Tri.UNKNOWN and c.missing_info and c.meta.get("kind") != "entrance":
            out.append(("Missing data", f"{c.missing_info} was left blank, treated as UNKNOWN."))
    for c, m in borderline_items(r):
        out.append(("Borderline mark", f"{c.label}: {abs(m):g} point(s) {'above' if m >= 0 else 'below'} the threshold."))
    if (r.source or {}).get("verification_status") != "Verified":
        out.append(("Unverified rule", "This rule is an illustrative sample, not an official criterion."))
    out.append(("Not modelled", NOT_MODELLED))
    return out


def reasoning_chain(r: EvaluationResult) -> list:
    """Ordered steps from student input to conclusion; every conclusion carries its own evidence."""
    steps = []
    for i, c in enumerate(r.conditions, 1):
        d = explain_condition(c)
        step = {"n": i, **d, "children": [explain_condition(k) for k in c.children]}
        steps.append(step)
    return steps


def conclusion_sentence(r: EvaluationResult) -> str:
    return r.final_explanation


def programme_cards(profile: dict, kb: dict) -> list:
    profile = normalise_profile(profile)
    out = []
    for r in evaluate_all(profile, kb):
        a = analyse(r)
        out.append({"result": r, "id": r.programme_id, "name": r.programme_name, "level": r.level, "field": r.field,
                    "decision": r.decision, "confidence": confidence(r), "review": review_state(r, profile),
                    "passed": len(r.passed), "failed": len(r.failed), "unknown": len(r.unknown), "total": len(r.conditions),
                    "analysis": a, "exceptions": exceptions(r, profile),
                    "headline": _headline(r)})
    order = {ELIGIBLE: 0, NEEDS_REVIEW: 1, NOT_ELIGIBLE: 2}
    out.sort(key=lambda c: (order[c["decision"]], len(c["result"].failed), c["name"]))
    return out


def _headline(r: EvaluationResult) -> str:
    if r.decision == ELIGIBLE:
        return "You meet every requirement."
    parts = [f"{c.label.split(' (')[0]}: {c.gap_text.replace(' percentage points', ' pts short')}" for c in r.failed]
    if r.decision == NEEDS_REVIEW:
        return "Still needed: " + "; ".join(m.split(" for: ")[0] for m in r.missing_information)
    return "; ".join(parts) or "Requirement not met."


# ------------------------------------------------------------------ pathways
def pathways(profile: dict, target_id: str, kb: dict) -> list:
    """Feasible alternative routes to a target programme, each with its prerequisite dependencies."""
    out = []
    for e in find_routes(profile, target_id, kb):
        entry = e["entry"]
        out.append({
            "name": e["name"], "type": e["route_type"], "start": e["entry_decision"], "why": e["why"], "why_now": e["why_now"],
            "chain": [(s["kind"], s["label"], s["status"]) for s in e["steps"]],
            "blocking": [(c.label, c.gap_text if c.result is Tri.FALSE else "Information needed") for c in e["missing"]],
            "to_do": e["steps_to_complete"], "recognition": e["recognition_note"] or e["officially_recognised"],
            "verification": e["verification_status"], "disclaimer": e["disclaimer"],
            "feasible_now": e["entry_decision"] == ELIGIBLE, "final": e["final_programme"],
            "entry_rule": entry.rule_expression if entry else "",
        })
    return out


def pathway_overview(profile: dict, kb: dict) -> list:
    """For every programme the applicant is not eligible for: is there a route they could start today?"""
    rows = []
    for card in programme_cards(profile, kb):
        if card["decision"] == ELIGIBLE:
            continue
        routes = pathways(profile, card["id"], kb)
        ready = [x for x in routes if x["feasible_now"]]
        rows.append({"id": card["id"], "name": card["name"], "decision": card["decision"], "routes": len(routes),
                     "ready": [x["name"] for x in ready]})
    return rows


# ------------------------------------------------------------ baseline compare
def baseline_comparison(profile: dict, kb: dict) -> list:
    """Per-programme: rule engine vs the simple if/else baseline (missing treated as zero)."""
    profile = normalise_profile(profile)
    rows = []
    for r in evaluate_all(profile, kb):
        base = baseline_eligible(profile, prog_by_id(kb, r.programme_id))
        base_txt = "Eligible" if base else "Not eligible"
        if base and r.decision == NOT_ELIGIBLE:
            note = "Baseline would wrongly say Eligible"
        elif base and r.decision == NEEDS_REVIEW:
            note = "Baseline guesses; engine asks for the missing data"
        elif not base and r.decision == ELIGIBLE:
            note = "Baseline would wrongly reject you"
        elif not base and r.decision == NEEDS_REVIEW:
            note = "Baseline silently counts blanks as failures"
        else:
            note = "Same answer"
        rows.append({"name": r.programme_name, "engine": r.decision, "baseline": base_txt, "note": note, "agree": note == "Same answer"})
    return rows


# ------------------------------------------------ representative KB test cases
def _p(**over) -> dict:
    p = {"student_id": "CASE", "name": "", "class10_pct": 80, "class12_pct": 70, "stream": "Science (PCM)", "overall_pct": 70,
         "marks": {"mathematics": 70, "physics": 60, "chemistry": 60, "english": 60},
         "entrance_exams": {"JEE Main": {"status": "Qualified", "score": 90}},
         "diploma": {"has": False}, "bachelor": {"has": False}, "certificates": []}
    for k, v in over.items():
        p[k] = {**p[k], **v} if k == "marks" else v
    return normalise_profile(p)


# (kind, name, assumption, profile, programme_id, acceptance criterion = expected decision)
CASES = [
    ("Normal", "Strong PCM applicant", "All marks comfortably above every threshold; JEE Main qualified.", _p(), "btech_cse", ELIGIBLE),
    ("Normal", "Weak maths, no entrance", "Overall 58, Maths 45, JEE Main not taken (the brief's example).",
     _p(overall_pct=58, marks={"mathematics": 45}, entrance_exams={"JEE Main": {"status": "Not taken"}}), "btech_cse", NOT_ELIGIBLE),
    ("Edge", "Exactly on every threshold", "Overall 65, Maths 60, Physics 45: '>=' means equal marks pass.",
     _p(overall_pct=65, marks={"mathematics": 60, "physics": 45}), "btech_cse", ELIGIBLE),
    ("Edge", "0.1 below a threshold", "Overall 64.9 against a minimum of 65 fails, with a 0.1 gap.",
     _p(overall_pct=64.9), "btech_cse", NOT_ELIGIBLE),
    ("Incomplete", "Maths left blank", "Blank is UNKNOWN, never a guess: no FALSE, so the outcome is Needs review.",
     _p(marks={"mathematics": None}), "btech_cse", NEEDS_REVIEW),
    ("Incomplete", "Blank maths but failed physics", "FALSE dominates UNKNOWN: physics 30 < 45 is enough for Not eligible.",
     _p(marks={"mathematics": None, "physics": 30}), "btech_cse", NOT_ELIGIBLE),
    ("Incomplete", "Entrance result awaited", "Pending result is UNKNOWN, so the outcome is Needs review, not a rejection.",
     _p(entrance_exams={"JEE Main": {"status": "Appeared - result awaited"}}), "btech_cse", NEEDS_REVIEW),
]


def run_cases(kb: dict) -> list:
    rows = []
    for kind, name, assumption, profile, pid, expected in CASES:
        got = evaluate_programme(profile, prog_by_id(kb, pid), cert_names(kb)).decision
        rows.append({"kind": kind, "name": name, "assumption": assumption, "programme": prog_by_id(kb, pid)["name"],
                     "expected": expected, "actual": got, "pass": got == expected})
    return rows


def kb_summary(kb: dict) -> dict:
    levels, status = {}, {}
    for p in kb["programmes"]:
        levels[p["level"]] = levels.get(p["level"], 0) + 1
        s = (p.get("source") or {}).get("verification_status", "Unverified")
        status[s] = status.get(s, 0) + 1
    rules = sum(len(evaluate_programme(normalise_profile({}), p).conditions) for p in kb["programmes"])
    return {"programmes": len(kb["programmes"]), "routes": len(kb["routes"]), "certificates": len(kb["certificates"]),
            "rules": rules, "levels": levels, "verification": status}


ASSUMPTIONS = [
    "All thresholds, routes and progression links are illustrative samples, not official requirements.",
    "A programme is a conjunction (AND) of requirement predicates; OR-groups are modelled explicitly as alternatives.",
    "Three-valued logic: any FALSE gives Not eligible; otherwise any UNKNOWN gives Needs review; otherwise Eligible.",
    "Blank, invalid or out-of-range inputs are UNKNOWN. Nothing is imputed or guessed.",
    "Entrance results marked registered or awaited are UNKNOWN by design.",
    "A certificate affects formal eligibility only when a programme rule names it explicitly.",
    "Confidence is a deterministic completeness label, not a probability.",
]
