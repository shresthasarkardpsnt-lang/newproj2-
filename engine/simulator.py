"""What-if simulator. Works on a deep copy: the stored student profile is never modified."""
from __future__ import annotations
import copy
from typing import Optional

from .constants import ELIGIBLE, NOT_ELIGIBLE
from .eligibility import evaluate_all
from .logic import Tri
from .validation import normalise_profile

HYPOTHETICAL = "HYPOTHETICAL - simulated values only; your real profile and marks are unchanged."


def apply_overrides(profile: dict, overrides: dict) -> dict:
    p = normalise_profile(profile)  # normalise_profile returns a deep copy
    for key in ("overall_pct", "class10_pct", "stream"):
        if key in overrides and overrides[key] is not None:
            p[key] = overrides[key]
    for subj, val in (overrides.get("marks") or {}).items():
        if val is None:
            continue
        if subj in p["marks"] or subj in ("mathematics", "physics", "chemistry", "biology", "computer_science", "english"):
            p["marks"][subj] = val
            p["studied"][subj] = True
        else:
            p["other_subjects"][subj] = val
    for ex, d in (overrides.get("entrance_exams") or {}).items():
        p["entrance_exams"][ex] = dict(d)
    return p


def simulate(profile: dict, overrides: dict, kb: dict) -> dict:
    original = copy.deepcopy(profile)
    hypo_profile = apply_overrides(profile, overrides or {})
    cur, hyp = evaluate_all(profile, kb), evaluate_all(hypo_profile, kb)
    rows, newly, lost, transitions, remaining = [], [], [], [], {}
    for c, h in zip(cur, hyp):
        rows.append({"Programme": c.programme_name, "Current": c.decision, "Hypothetical": h.decision,
                     "Changed": "Yes" if c.decision != h.decision else "No"})
        if c.decision != ELIGIBLE and h.decision == ELIGIBLE:
            newly.append(c.programme_name)
        if c.decision == ELIGIBLE and h.decision != ELIGIBLE:
            lost.append(c.programme_name)
        cmap = {x.req_id: x for x in c.conditions}
        for hc in h.conditions:
            cc = cmap.get(hc.req_id)
            if cc is not None and cc.result != hc.result:
                transitions.append({"Programme": c.programme_name, "Condition": hc.label,
                                    "From": cc.result.value, "To": hc.result.value})
        if h.failed:
            remaining[c.programme_name] = [(x.label, x.gap_text) for x in h.failed]
    return {"label": HYPOTHETICAL, "hypothetical_profile": hypo_profile, "current": cur, "hypothetical": hyp,
            "rows": rows, "newly_eligible": newly, "no_longer_eligible": lost, "transitions": transitions,
            "false_to_true": [t for t in transitions if t["From"] == "FALSE" and t["To"] == "TRUE"],
            "remaining_failed": remaining, "profile_unchanged": original == profile}
