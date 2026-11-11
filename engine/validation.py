"""Student-profile defaults, normalisation and validation."""
from __future__ import annotations
import copy
from typing import Optional

from .constants import CORE_SUBJECTS, ENTRANCE_STATUSES
from .logic import to_number

PERCENT_FIELDS = {"class10_pct": "Class 10 percentage", "class12_pct": "Class 12 percentage",
                  "overall_pct": "Overall percentage"}


def default_profile(student_id: str = "") -> dict:
    return {
        "student_id": student_id, "name": "", "class10_pct": None, "class12_pct": None,
        "stream": None, "overall_pct": None,
        "marks": {s: None for s in CORE_SUBJECTS}, "other_subjects": {},
        "studied": {s: None for s in CORE_SUBJECTS},
        "entrance_exams": {},
        "diploma": {"has": None, "branch": None, "pct": None},
        "bachelor": {"has": None, "degree": "", "discipline": None, "pct": None},
        "additional_qualifications": [], "certificates": [],
        "preferred_programme": None, "career_interests": [],
    }


def normalise_profile(profile: Optional[dict]) -> dict:
    """Return a deep copy with every expected key present (never mutates input)."""
    base = default_profile()
    src = copy.deepcopy(profile or {})
    for key, default in base.items():
        if key not in src or src[key] is None and isinstance(default, (dict, list)):
            src[key] = copy.deepcopy(default)
    for key in ("marks", "studied"):
        for s in CORE_SUBJECTS:
            src[key].setdefault(s, None)
    for key in ("diploma", "bachelor"):
        for k, v in base[key].items():
            src[key].setdefault(k, v)
    return src


def is_studied(profile: dict, subject: str) -> Optional[bool]:
    """Studied = explicit flag, or implied by an entered mark; None when unknown."""
    flag = profile.get("studied", {}).get(subject)
    if flag is False:
        return False
    if flag is True:
        return True
    return True if get_mark(profile, subject) is not None else None


def get_mark(profile: dict, subject: str) -> Optional[float]:
    marks = profile.get("marks", {}) or {}
    if subject in marks:
        return to_number(marks[subject])
    return to_number((profile.get("other_subjects", {}) or {}).get(subject))


def validate_profile(profile: dict) -> tuple:
    """Return (errors, warnings). Errors block saving; warnings are informational."""
    p = normalise_profile(profile)
    errors, warnings = [], []
    if not str(p["student_id"]).strip():
        errors.append("Student ID or name is required.")
    raw = profile or {}
    for key, label in PERCENT_FIELDS.items():
        val = raw.get(key)
        if val not in (None, "") and to_number(val) is None:
            errors.append(f"{label} must be a number between 0 and 100 (got {val!r}).")
    for s, val in (raw.get("marks") or {}).items():
        if val not in (None, "") and to_number(val) is None:
            errors.append(f"{s.replace('_', ' ').title()} marks must be between 0 and 100 (got {val!r}).")
    for s, val in (raw.get("other_subjects") or {}).items():
        if val not in (None, "") and to_number(val) is None:
            errors.append(f"{s} marks must be between 0 and 100 (got {val!r}).")
    for key in ("diploma", "bachelor"):
        val = (raw.get(key) or {}).get("pct")
        if val not in (None, "") and to_number(val) is None:
            errors.append(f"{key.title()} percentage must be between 0 and 100 (got {val!r}).")
    for ex, d in (raw.get("entrance_exams") or {}).items():
        d = d or {}
        if d.get("status") not in (None, *ENTRANCE_STATUSES):
            errors.append(f"{ex}: unknown status {d.get('status')!r}.")
        sc = d.get("score")
        if sc not in (None, "") and to_number(sc, 0, 1e9) is None:
            errors.append(f"{ex}: score must be a non-negative number (got {sc!r}).")
        if d.get("status") == "Qualified" and sc in (None, ""):
            warnings.append(f"{ex}: marked Qualified without a score (fine unless a rule needs a minimum score).")
    for s in CORE_SUBJECTS:
        if p["studied"].get(s) is False and get_mark(p, s) is not None:
            errors.append(f"{s.replace('_', ' ').title()} is marked 'not studied' but marks were entered.")
    if p["bachelor"].get("has") and p["bachelor"].get("pct") is None:
        warnings.append("Bachelor's degree held but percentage is missing.")
    if p["diploma"].get("has") and p["diploma"].get("pct") is None:
        warnings.append("Diploma held but percentage is missing.")
    missing = [lab for k, lab in PERCENT_FIELDS.items() if p.get(k) is None]
    if missing:
        warnings.append("Missing (will be treated as UNKNOWN): " + ", ".join(missing) + ".")
    return errors, warnings
