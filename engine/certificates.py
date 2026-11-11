"""Certificate recommendation and impact analysis.

Rule: a certificate NEVER changes marks or formal eligibility by itself. The only way a
certificate affects eligibility is when a programme requirement explicitly names it
(type 'certificate'), which is recorded in the knowledge base.
"""
from __future__ import annotations
import copy
from typing import Optional

from .constants import (CERT_CATEGORIES, FIELD_AREAS, INTEREST_AREAS, SUBJECT_AREA, TECHNICAL_FIELDS)
from .eligibility import evaluate_all, evaluate_programme
from .kb import cert_names, certificate_links, prog_by_id, walk_requirements
from .logic import Tri
from .validation import normalise_profile

NO_PROBABILITY = ("Match strength is a rule-based count of matching factors. It is not an admission probability and "
                  "no admission benefit is implied unless the institution explicitly accepts the certificate.")
NON_SCIENCE = ("Commerce", "Arts / Humanities", "Vocational", "Other", "Science (PCB)")


def cert_flags(cert: dict, kb: dict) -> dict:
    linked = certificate_links(kb, cert["id"])
    imp = cert.get("impact", {}) or {}
    verified = bool(linked) and all((p.get("source", {}) or {}).get("verification_status") == "Verified" for p in linked)
    return {"improves_formal_eligibility": bool(linked), "formal_programmes": [p["name"] for p in linked],
            "improves_academic_preparation": bool(imp.get("academic_preparation")),
            "strengthens_profile": bool(imp.get("profile_strengthening")),
            "admission_recognition_unverified": not verified}


def knowledge_gaps(profile: dict, kb: dict, target_id: Optional[str]) -> list:
    profile = normalise_profile(profile)
    gaps = {}

    def add(area, reason):
        gaps.setdefault(area, []).append(reason)
    target = prog_by_id(kb, target_id) if target_id else None
    if target:
        res = evaluate_programme(profile, target, cert_names(kb))
        for c in res.failed + res.unknown:
            subj = c.meta.get("subject")
            if subj in SUBJECT_AREA:
                state = f"gap of {c.gap_text}" if c.result is Tri.FALSE else "marks not provided"
                add(SUBJECT_AREA[subj], f"{c.label}: {state}")
        if target["field"] in TECHNICAL_FIELDS:
            if profile.get("stream") in NON_SCIENCE:
                add("mathematics", f"Background: stream is {profile['stream']}; technical programmes build on mathematics (general guidance, not an admission rule)")
                add("programming", f"Background: stream is {profile['stream']}; technical programmes build on programming (general guidance, not an admission rule)")
            cs = profile["studied"].get("computer_science")
            if cs is False or (cs is None and profile["marks"].get("computer_science") in (None, "")):
                add("programming", "No Computer Science background recorded")
    return [{"area": a, "reasons": r} for a, r in gaps.items()]


def recommend(profile: dict, kb: dict, target_id: Optional[str] = None, include_completed: bool = False) -> list:
    profile = normalise_profile(profile)
    target = prog_by_id(kb, target_id) if target_id else None
    field = target["field"] if target else None
    field_areas = FIELD_AREAS.get(field, [])
    gaps = {g["area"]: "; ".join(g["reasons"]) for g in knowledge_gaps(profile, kb, target_id)}
    interest_areas = {a for i in profile.get("career_interests", []) for a in INTEREST_AREAS.get(i, [])}
    interest_of = {a: i for i in profile.get("career_interests", []) for a in INTEREST_AREAS.get(i, [])}
    linked_ids = set()
    if target:
        for r in walk_requirements(target["requirements"]):
            if r["type"] == "certificate":
                linked_ids.update(r["certificates"])
    completed = set(profile.get("certificates", []))
    out = []
    for c in kb["certificates"]:
        if c["id"] in completed and not include_completed:
            continue
        reasons, score = [], 0
        if c["id"] in linked_ids:
            score += 3
            reasons.append(f"Named as an accepted certificate in the sample rule for {target['name']}.")
        for a in c.get("knowledge_areas", []):
            if a in gaps:
                score += 2
                reasons.append(f"Covers a knowledge gap in {a.replace('_', ' ')} ({gaps[a]}).")
            elif a in field_areas:
                score += 1
                reasons.append(f"Builds {a.replace('_', ' ')}, which {field} programmes rely on.")
            if a in interest_areas:
                score += 1
                reasons.append(f"Matches your career interest '{interest_of[a]}'.")
        if field and field in c.get("fields", []):
            score += 1
            reasons.append(f"Listed for the {field} field.")
        if score == 0:
            continue
        flags = cert_flags(c, kb)
        flags["improves_target_eligibility"] = c["id"] in linked_ids
        out.append({**c, "score": score, "relevance": "High" if score >= 4 else "Medium" if score >= 2 else "Low",
                    "reasons": reasons, "flags": flags, "completed": c["id"] in completed,
                    "duration_display": c.get("duration") or "Not verified",
                    "cost_display": c.get("cost") or "Not verified"})
    out.sort(key=lambda x: (CERT_CATEGORIES.index(x["category"]) if x["category"] in CERT_CATEGORIES else 9, -x["score"], x["name"]))
    return out


def certificate_impact(profile: dict, cert_id: str, kb: dict) -> dict:
    """Compare eligibility before/after marking a certificate as completed. Marks are never touched."""
    before_p = normalise_profile(profile)
    after_p = copy.deepcopy(before_p)
    if cert_id not in after_p["certificates"]:
        after_p["certificates"].append(cert_id)
    before, after = evaluate_all(before_p, kb), evaluate_all(after_p, kb)
    changes = []
    for b, a in zip(before, after):
        cond_changes = [(cb.label, cb.result.value, ca.result.value)
                        for cb, ca in zip(b.conditions, a.conditions) if cb.result != ca.result]
        if b.decision != a.decision or cond_changes:
            changes.append({"programme": b.programme_name, "before": b.decision, "after": a.decision,
                            "conditions_changed": cond_changes})
    same_marks = (before_p["marks"] == after_p["marks"] and before_p["overall_pct"] == after_p["overall_pct"]
                  and before_p["stream"] == after_p["stream"])
    return {"certificate_id": cert_id, "changes": changes, "marks_unchanged": same_marks,
            "formal_change": bool(changes)}
