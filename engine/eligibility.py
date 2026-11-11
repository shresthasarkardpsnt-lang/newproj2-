"""Rule-based eligibility evaluation using three-valued predicate logic.

Every programme is a conjunction of requirement predicates. Each predicate is
evaluated against the student profile and returns TRUE / FALSE / UNKNOWN along
with the student input, the rule, evidence, an explanation and any missing
information. No scores, probabilities or learned models are involved.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional

from .constants import (ELIGIBLE, ENTRANCE_NOT_SPECIFIED, ENTRANCE_PENDING, NEEDS_REVIEW,
                        NOT_ELIGIBLE, SUBJECT_LABELS)
from .logic import Tri, compare, fmt, member_of, to_number, tri_and, tri_from_bool, tri_or
from .validation import get_mark, is_studied, normalise_profile


@dataclass
class ConditionResult:
    req_id: str
    label: str
    rtype: str
    rule: str
    student_value: str
    required: str
    result: Tri
    gap: Optional[float] = None
    gap_text: str = ""
    evidence: str = ""
    explanation: str = ""
    missing_info: Optional[str] = None
    meta: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["result"] = self.result.value
        d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass
class EvaluationResult:
    programme_id: str
    programme_name: str
    level: str
    field: str
    decision: str
    conditions: list
    rule_expression: str
    rule_version: int
    source: dict
    final_explanation: str

    @property
    def passed(self): return [c for c in self.conditions if c.result is Tri.TRUE]
    @property
    def failed(self): return [c for c in self.conditions if c.result is Tri.FALSE]
    @property
    def unknown(self): return [c for c in self.conditions if c.result is Tri.UNKNOWN]
    @property
    def missing_information(self): return [c.missing_info for c in self.unknown if c.missing_info]

    def to_dict(self) -> dict:
        return {"programme_id": self.programme_id, "programme_name": self.programme_name,
                "level": self.level, "field": self.field, "decision": self.decision,
                "rule_expression": self.rule_expression, "rule_version": self.rule_version,
                "source": self.source, "final_explanation": self.final_explanation,
                "conditions": [c.to_dict() for c in self.conditions]}


def _gap_text(result: Tri, gap: Optional[float]) -> str:
    if result is Tri.TRUE:
        return "Satisfied"
    if result is Tri.UNKNOWN:
        return "Unknown - information missing"
    return f"{fmt(gap)} percentage points" if gap is not None else "Not met"


def _src(prog: dict) -> str:
    s = prog.get("source", {}) or {}
    return f"{s.get('name', 'unknown source')} [{s.get('verification_status', 'Unverified')}], rule v{prog.get('rule_version', 1)}"


def _mk(req, prog, *, label, rule, student_value, required, result, gap=None, evidence_field,
        explanation, missing=None, meta=None, rid=None) -> ConditionResult:
    return ConditionResult(
        req_id=rid or req["id"], label=label, rtype=req["type"], rule=rule, student_value=student_value,
        required=required, result=result, gap=gap, gap_text=_gap_text(result, gap),
        evidence=f"Student record: {evidence_field}. Requirement source: {_src(prog)}.",
        explanation=explanation, missing_info=missing if result is Tri.UNKNOWN else None, meta=meta or {})


def _numeric(req, prog, *, label, rule_name, value, threshold, field_desc, missing_desc, meta) -> ConditionResult:
    result = compare(value, ">=", threshold)
    gap = None
    if result is Tri.FALSE:
        gap = round(threshold - value, 6)
    if result is Tri.TRUE:
        expl = f"{label} is {fmt(value)}%, which meets the minimum of {fmt(threshold)}% (margin {fmt(value - threshold)} points)."
    elif result is Tri.FALSE:
        expl = f"{label} is {fmt(value)}%, which is {fmt(gap)} percentage points below the minimum of {fmt(threshold)}%."
    else:
        expl = f"{label} was not provided (or was invalid), so the requirement of {fmt(threshold)}% cannot be checked."
    return _mk(req, prog, label=label, rule=f"{rule_name} >= {fmt(threshold)}",
               student_value=f"{fmt(value)}%" if value is not None else "Not provided",
               required=f"{fmt(threshold)}%", result=result, gap=gap,
               evidence_field=f"{field_desc} = {fmt(value) + '%' if value is not None else 'not provided'}",
               explanation=expl, missing=missing_desc, meta=meta)


def _subject_label(subject: str) -> str:
    return SUBJECT_LABELS.get(subject, subject.replace("_", " ").title())


def _min_subject(req, prog, profile) -> ConditionResult:
    subj = req["subject"]
    label = _subject_label(subj)
    studied = is_studied(profile, subj)
    mark = get_mark(profile, subj)
    meta = {"subject": subj, "kind": "numeric"}
    if studied is False:
        return _mk(req, prog, label=f"{label} marks", rule=f"{label} >= {fmt(req['min'])}",
                   student_value="Subject not studied", required=f"{fmt(req['min'])}%", result=Tri.FALSE,
                   evidence_field=f"{label} marked as not studied",
                   explanation=f"{label} was not studied, so the required mark of {fmt(req['min'])}% cannot be met.",
                   meta={**meta, "not_studied": True})
    return _numeric(req, prog, label=f"{label} marks", rule_name=label, value=mark, threshold=req["min"],
                    field_desc=f"{label} marks", missing_desc=f"{label} marks", meta=meta)


def _subject_studied(req, prog, profile) -> ConditionResult:
    subj = req["subject"]
    label = _subject_label(subj)
    studied = is_studied(profile, subj)
    result = tri_from_bool(studied)
    sv = {True: "Studied", False: "Not studied", None: "Not provided"}[studied]
    expl = {Tri.TRUE: f"{label} was studied.", Tri.FALSE: f"{label} was not studied but is required.",
            Tri.UNKNOWN: f"It is not known whether {label} was studied."}[result]
    return _mk(req, prog, label=f"{label} studied", rule=f"{label.replace(' ', '_')}_Studied == True",
               student_value=sv, required="Studied", result=result,
               evidence_field=f"{label} studied = {sv.lower()}", explanation=expl,
               missing=f"Whether {label} was studied (or its marks)", meta={"subject": subj, "kind": "categorical"})


def _stream_in(req, prog, profile) -> ConditionResult:
    stream = profile.get("stream")
    result = member_of(stream, req["values"])
    vals = ", ".join(req["values"])
    expl = {Tri.TRUE: f"Stream '{stream}' is accepted.",
            Tri.FALSE: f"Stream '{stream}' is not in the accepted list ({vals}).",
            Tri.UNKNOWN: "Academic stream was not provided."}[result]
    return _mk(req, prog, label=req.get("label", "Academic stream"), rule=f"Stream IN {{{vals}}}",
               student_value=stream or "Not provided", required=vals, result=result,
               evidence_field=f"Stream = {stream or 'not provided'}", explanation=expl,
               missing="Academic stream", meta={"kind": "categorical"})


def _entrance(req, prog, profile) -> ConditionResult:
    exams, min_score = req["exams"], req.get("min_score")
    exam_data = profile.get("entrance_exams") or {}
    tris, parts, unknown_exams, gaps = [], [], [], []
    for ex in exams:
        d = exam_data.get(ex) or {}
        status = d.get("status") or ENTRANCE_NOT_SPECIFIED
        score = to_number(d.get("score"), 0, 1e9)
        if status == ENTRANCE_NOT_SPECIFIED:
            t = Tri.UNKNOWN
        elif status == "Not taken":
            t = Tri.FALSE
        elif status in ENTRANCE_PENDING:
            t = Tri.UNKNOWN
        elif status == "Qualified":
            if min_score is None:
                t = Tri.TRUE
            elif score is None:
                t = Tri.UNKNOWN
            else:
                t = compare(score, ">=", min_score)
                if t is Tri.FALSE:
                    gaps.append(round(min_score - score, 6))
        else:
            t = Tri.FALSE
        if t is Tri.UNKNOWN:
            unknown_exams.append(ex)
        tris.append(t)
        parts.append(f"{ex}: {status}" + (f" (score {fmt(score)})" if score is not None else ""))
    result = tri_or(tris)
    gap = gaps[0] if (len(exams) == 1 and gaps and result is Tri.FALSE) else None
    names = " OR ".join(exams)
    rule = f"Entrance({names}) == Qualified" + (f" AND Score >= {fmt(min_score)}" if min_score is not None else "")
    expl = {Tri.TRUE: "At least one accepted entrance examination is qualified: " + "; ".join(parts) + ".",
            Tri.FALSE: "None of the accepted entrance examinations is qualified: " + "; ".join(parts) + ".",
            Tri.UNKNOWN: "Entrance status is incomplete or pending: " + "; ".join(parts) + "."}[result]
    return _mk(req, prog, label=req.get("label", "Entrance examination"), rule=rule,
               student_value="; ".join(parts), required=f"Qualified in {names}", result=result, gap=gap,
               evidence_field="Entrance status - " + "; ".join(parts), explanation=expl,
               missing="Entrance status / result for: " + ", ".join(unknown_exams or exams),
               meta={"kind": "entrance", "exams": exams})


def _qualification(req, prog, profile) -> list:
    level = req["level"]
    data = profile.get(level) or {}
    name = "Bachelor's degree" if level == "bachelor" else "Diploma"
    key = "discipline" if level == "bachelor" else "branch"
    has = data.get("has")
    out = [_mk(req, prog, label=f"{name} held", rule=f"{level.title()}_Held == True",
               student_value={True: "Yes", False: "No", None: "Not provided"}[has], required="Yes",
               result=tri_from_bool(has), rid=f"{req['id']}_held",
               evidence_field=f"{name} held = {has}",
               explanation={True: f"{name} is held.", False: f"No {name.lower()} is held but one is required.",
                            None: f"It is not known whether a {name.lower()} is held."}[has],
               missing=f"Whether a {name.lower()} is held", meta={"kind": "categorical", "level": level})]
    if has is False:
        return out
    if req.get("min_pct") is not None:
        out.append(_numeric({**req, "id": f"{req['id']}_pct"}, prog, label=f"{name} percentage",
                            rule_name=f"{level.title()}_Percentage", value=to_number(data.get("pct")),
                            threshold=req["min_pct"], field_desc=f"{name} percentage",
                            missing_desc=f"{name} percentage", meta={"kind": "numeric", "level": level}))
    if req.get("disciplines"):
        val = data.get(key)
        res = member_of(val, req["disciplines"])
        dl = ", ".join(req["disciplines"])
        out.append(_mk(req, prog, label=f"{name} {key}", rule=f"{level.title()}_{key.title()} IN {{{dl}}}",
                       student_value=val or "Not provided", required=dl, result=res, rid=f"{req['id']}_{key}",
                       evidence_field=f"{name} {key} = {val or 'not provided'}",
                       explanation={Tri.TRUE: f"{key.title()} '{val}' is accepted.",
                                    Tri.FALSE: f"{key.title()} '{val}' is not in the accepted list ({dl}).",
                                    Tri.UNKNOWN: f"{name} {key} was not provided."}[res],
                       missing=f"{name} {key}", meta={"kind": "categorical", "level": level}))
    return out


def _certificate(req, prog, profile, cert_names) -> ConditionResult:
    ids = req["certificates"]
    held = set(profile.get("certificates") or [])
    result = tri_from_bool(any(c in held for c in ids))
    names = [(cert_names or {}).get(c, c) for c in ids]
    return _mk(req, prog, label=req.get("label", "Accepted certificate"),
               rule="Certificate IN {" + ", ".join(ids) + "}",
               student_value=", ".join((cert_names or {}).get(c, c) for c in held if c in ids) or "None completed",
               required=" OR ".join(names), result=result,
               evidence_field="Completed certificates = " + (", ".join(sorted(held)) or "none"),
               explanation=("An accepted certificate is completed." if result is Tri.TRUE else
                            "No certificate accepted by this rule has been completed. Per this sample rule it is "
                            "accepted only because the rule names it explicitly."),
               meta={"kind": "certificate", "certificates": ids})


def evaluate_requirement(req, prog, profile, cert_names=None) -> list:
    t = req["type"]
    if t == "min_overall":
        return [_numeric(req, prog, label=req.get("label", "Overall percentage"), rule_name="Overall",
                         value=to_number(profile.get("overall_pct")), threshold=req["min"],
                         field_desc="Overall percentage", missing_desc="Overall percentage (Class 12 / equivalent)",
                         meta={"kind": "numeric", "subject": "overall"})]
    if t == "min_class10":
        return [_numeric(req, prog, label=req.get("label", "Class 10 percentage"), rule_name="Class10",
                         value=to_number(profile.get("class10_pct")), threshold=req["min"],
                         field_desc="Class 10 percentage", missing_desc="Class 10 percentage",
                         meta={"kind": "numeric", "subject": "class10"})]
    if t == "min_subject":
        return [_min_subject(req, prog, profile)]
    if t == "subject_studied":
        return [_subject_studied(req, prog, profile)]
    if t == "stream_in":
        return [_stream_in(req, prog, profile)]
    if t == "entrance":
        return [_entrance(req, prog, profile)]
    if t == "qualification":
        return _qualification(req, prog, profile)
    if t == "certificate":
        return [_certificate(req, prog, profile, cert_names)]
    if t == "any_of":
        child_groups = [evaluate_requirement(o, prog, profile, cert_names) for o in req["options"]]
        flat = [c for g in child_groups for c in g]
        res = tri_or([tri_and(c.result for c in g) for g in child_groups])
        gaps = [c.gap for c in flat if c.gap is not None]
        gap = min(gaps) if (res is Tri.FALSE and gaps) else None
        opts = " OR ".join(c.rule for c in flat)
        missing = "; ".join(m for m in (c.missing_info for c in flat if c.result is Tri.UNKNOWN) if m)
        expl = {Tri.TRUE: "At least one of the alternative conditions is satisfied.",
                Tri.FALSE: "None of the alternative conditions is satisfied: " + "; ".join(c.explanation for c in flat),
                Tri.UNKNOWN: "No alternative is satisfied yet, and some cannot be checked: " + (missing or "information missing")}[res]
        return _any_of_condition(req, prog, res, gap, opts, expl, missing, flat)
    raise ValueError(f"Unknown requirement type: {t}")


def _any_of_condition(req, prog, res, gap, opts, expl, missing, flat) -> list:
    parent = _mk(req, prog, label=req.get("label", "One of several alternatives"), rule=f"({opts})",
                 student_value=" | ".join(c.student_value for c in flat), required="At least one alternative",
                 result=res, gap=gap,
                 evidence_field="alternatives checked - " + " | ".join(f"{c.label}: {c.student_value}" for c in flat),
                 explanation=expl, missing=missing or "Information for the alternatives", meta={"kind": "any_of"})
    parent.children = flat
    return [parent]


def _decide(conditions) -> str:
    res = tri_and(c.result for c in conditions)
    return {Tri.TRUE: ELIGIBLE, Tri.FALSE: NOT_ELIGIBLE, Tri.UNKNOWN: NEEDS_REVIEW}[res]


def _final_explanation(decision, conditions) -> str:
    n = len(conditions)
    failed = [c for c in conditions if c.result is Tri.FALSE]
    unknown = [c for c in conditions if c.result is Tri.UNKNOWN]
    if decision == ELIGIBLE:
        return f"All {n} conditions are TRUE, so the student is Eligible under this rule set."
    if decision == NOT_ELIGIBLE:
        txt = f"{len(failed)} of {n} conditions are FALSE ({', '.join(c.label for c in failed)}), so the student is Not eligible."
        if unknown:
            txt += f" {len(unknown)} further condition(s) are UNKNOWN."
        return txt
    return (f"No condition is FALSE, but {len(unknown)} of {n} cannot be determined "
            f"({', '.join(c.label for c in unknown)}), so the outcome is Needs review.")


def evaluate_programme(profile: dict, programme: dict, cert_names: Optional[dict] = None) -> EvaluationResult:
    profile = normalise_profile(profile)
    conditions = []
    for req in programme["requirements"]:
        conditions.extend(evaluate_requirement(req, programme, profile, cert_names))
    decision = _decide(conditions)
    return EvaluationResult(
        programme_id=programme["id"], programme_name=programme["name"], level=programme.get("level", ""),
        field=programme.get("field", ""), decision=decision, conditions=conditions,
        rule_expression=" AND ".join(c.rule for c in conditions),
        rule_version=programme.get("rule_version", 1), source=programme.get("source", {}),
        final_explanation=_final_explanation(decision, conditions))


def evaluate_all(profile: dict, kb: dict) -> list:
    from .kb import cert_names as _cn
    names = _cn(kb)
    return [evaluate_programme(profile, p, names) for p in kb["programmes"]]
