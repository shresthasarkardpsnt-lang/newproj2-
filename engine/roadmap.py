"""Personalised improvement roadmap. Completing items never changes marks or eligibility by itself."""
from __future__ import annotations

from .constants import ELIGIBLE
from .certificates import knowledge_gaps, recommend
from .eligibility import evaluate_programme
from .kb import cert_names, prog_by_id
from .missing import next_steps
from .pathway import find_routes
from .validation import normalise_profile

NOTE = ("Completing a course or certificate does not change your recorded marks. It affects formal eligibility only "
        "where a programme rule explicitly names that certificate.")


def build_roadmap(profile: dict, kb: dict, target_id: str, done_keys: set) -> dict:
    profile = normalise_profile(profile)
    target = prog_by_id(kb, target_id)
    res = evaluate_programme(profile, target, cert_names(kb))
    completed = set(profile["certificates"])
    stages = []

    items = []
    for c in res.failed + res.unknown:
        k = f"req:{target_id}:{c.req_id}"
        items.append({"key": k, "text": f"{c.label}: {c.gap_text} (required: {c.required})",
                      "detail": " ".join(next_steps(c)), "done": k in done_keys})
    stages.append({"stage": 1, "title": "Identify missing admission requirements", "items": items,
                   "empty": "All conditions are TRUE for this programme under the sample rule."})

    items = []
    for g in knowledge_gaps(profile, kb, target_id):
        k = f"gap:{target_id}:{g['area']}"
        items.append({"key": k, "text": f"Strengthen {g['area'].replace('_', ' ')}", "detail": "; ".join(g["reasons"]),
                      "done": k in done_keys})
    stages.append({"stage": 2, "title": "Identify academic knowledge gaps", "items": items,
                   "empty": "No knowledge gaps detected from your profile."})

    recs = recommend(profile, kb, target_id, include_completed=True)
    prep = [r for r in recs if r["category"] in ("Academic preparation courses", "Admission requirement certificates")][:3]
    prof = [r for r in recs if r["category"] in ("Professional skill certificates", "Profile-strengthening certificates")][:3]
    for num, title, lst in ((3, "Recommended learning courses", prep), (4, "Suitable certificates", prof)):
        stages.append({"stage": num, "title": title, "empty": "No matching recommendations.",
                       "items": [{"key": f"cert:{r['id']}", "cert_id": r["id"],
                                  "text": f"{r['name']} ({r['issuer']})",
                                  "detail": f"{r['category']}. " + " ".join(r["reasons"][:2]),
                                  "done": r["id"] in completed} for r in lst]})

    items = []
    for e in find_routes(profile, target_id, kb)[:3]:
        k = f"route:{e['id']}"
        items.append({"key": k, "text": f"Review route: {e['name']}",
                      "detail": f"Entry check: {e['entry_decision']}. Recognition: {e['officially_recognised']}; "
                                f"source status: {e['verification_status']}.", "done": k in done_keys,
                      "verified": e["verification_status"] == "Verified"})
    stages.append({"stage": 5, "title": "Consider alternative admission routes", "items": items,
                   "empty": "No alternative routes stored for this programme."})

    stages.append({"stage": 6, "title": "Track completed courses and certificates", "items": [],
                   "completed_certificates": sorted(completed), "empty": ""})
    stages.append({"stage": 7, "title": "Re-evaluate eligibility", "items": [], "decision": res.decision,
                   "explanation": res.final_explanation, "empty": ""})

    tracked = [i for s in stages for i in s["items"]]
    done = sum(1 for i in tracked if i["done"])
    return {"target": target["name"], "stages": stages, "done": done, "total": len(tracked),
            "progress": (done / len(tracked)) if tracked else 1.0, "decision": res.decision,
            "eligible": res.decision == ELIGIBLE, "note": NOTE}
