"""Higher eligibility opportunities: programmes with stricter thresholds than the student's current options."""
from __future__ import annotations
from typing import Optional

from .eligibility import EvaluationResult, evaluate_all
from .constants import ELIGIBLE
from .kb import prog_by_id, walk_requirements
from .logic import Tri, fmt, to_number

NOT_BETTER = ("Higher admission thresholds do not mean a better programme. Fit, curriculum and career goals matter "
              "more than the cut-off; this list only shows what would be required.")


def overall_threshold(programme: dict) -> Optional[float]:
    vals = [r["min"] for r in programme["requirements"] if r["type"] == "min_overall"]
    return max(vals) if vals else None


def subject_thresholds(programme: dict) -> dict:
    return {r["subject"]: r["min"] for r in walk_requirements(programme["requirements"]) if r["type"] == "min_subject"}


def entrance_requirements(programme: dict) -> list:
    out = []
    for r in walk_requirements(programme["requirements"]):
        if r["type"] == "entrance":
            out.append(" / ".join(r["exams"]))
    return out


def _row(res: EvaluationResult, prog: dict, reference: Optional[float]) -> dict:
    gaps = [c.gap for c in res.failed if c.gap is not None]
    ov = overall_threshold(prog)
    return {
        "Programme": res.programme_name, "Level": res.level, "Field": res.field, "Decision": res.decision,
        "Min overall %": ov, "Threshold vs reference": (None if ov is None or reference is None else round(ov - reference, 6)),
        "Subject minimums": ", ".join(f"{k.replace('_', ' ').title()} {fmt(v)}" for k, v in subject_thresholds(prog).items()) or "-",
        "Entrance exams": "; ".join(entrance_requirements(prog)) or "None in this rule set",
        "Total marks gap": round(sum(gaps), 6), "Failed": len(res.failed), "Unknown": len(res.unknown),
        "What is needed": "; ".join(f"{c.label}: {c.gap_text}" for c in res.failed)
                           + ("; " if res.failed and res.unknown else "")
                           + "; ".join(f"{c.label}: {c.missing_info}" for c in res.unknown if c.missing_info) or "Nothing - all conditions TRUE",
        "programme_id": res.programme_id,
    }


def analyse_higher(profile: dict, kb: dict, level: Optional[str] = None, field: Optional[str] = None) -> dict:
    results = evaluate_all(profile, kb)
    pool = [r for r in results if (level in (None, "All") or r.level == level) and (field in (None, "All") or r.field == field)]
    eligible = [r for r in pool if r.decision == ELIGIBLE]
    elig_thresholds = [t for t in (overall_threshold(prog_by_id(kb, r.programme_id)) for r in eligible) if t is not None]
    own = to_number(profile.get("overall_pct"))
    reference = max(elig_thresholds) if elig_thresholds else own
    basis = ("highest overall minimum among programmes you are currently eligible for" if elig_thresholds
             else "your own overall percentage" if own is not None else "none (overall percentage unknown)")
    higher = []
    for r in pool:
        if r.decision == ELIGIBLE:
            continue
        prog = prog_by_id(kb, r.programme_id)
        ov = overall_threshold(prog)
        if reference is not None and ov is not None and ov > reference:
            higher.append(_row(r, prog, reference))
    higher.sort(key=lambda x: (x["Total marks gap"], x["Failed"]))
    return {"eligible": [_row(r, prog_by_id(kb, r.programme_id), reference) for r in eligible],
            "higher": higher, "reference": reference, "reference_basis": basis, "disclaimer": NOT_BETTER}
