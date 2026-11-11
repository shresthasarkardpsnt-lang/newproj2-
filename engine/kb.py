"""Knowledge-base loading, lookup helpers and schema validation."""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Optional

from .constants import (CERT_CATEGORIES, DATA_DIR, LEVELS, RECOGNISED_VALUES, REQ_TYPES,
                        VERIFICATION_STATUSES)

ID_RE = re.compile(r"^[A-Za-z0-9_]+$")
KB_FILES = {"programmes": "programmes.json", "certificates": "certificates.json",
            "routes": "alternative_routes.json"}


def load_kb_from_json(data_dir: Optional[Path] = None) -> dict:
    data_dir = Path(data_dir or DATA_DIR)
    kb = {}
    for kind, fname in KB_FILES.items():
        with open(data_dir / fname, encoding="utf-8") as fh:
            kb[kind] = json.load(fh)
    return kb


def prog_by_id(kb: dict, pid: str) -> Optional[dict]:
    return next((p for p in kb["programmes"] if p["id"] == pid), None)


def cert_by_id(kb: dict, cid: str) -> Optional[dict]:
    return next((c for c in kb["certificates"] if c["id"] == cid), None)


def route_by_id(kb: dict, rid: str) -> Optional[dict]:
    return next((r for r in kb["routes"] if r["id"] == rid), None)


def cert_names(kb: dict) -> dict:
    return {c["id"]: c["name"] for c in kb["certificates"]}


def all_exams(kb: dict) -> list:
    """Every entrance exam referenced anywhere in the programme requirements."""
    found = []

    def walk(reqs):
        for r in reqs:
            if r.get("type") == "entrance":
                for e in r.get("exams", []):
                    if e not in found:
                        found.append(e)
            for opt in r.get("options", []) or []:
                walk([opt])
    for p in kb["programmes"]:
        walk(p.get("requirements", []))
    for r in kb.get("routes", []):
        walk(list((r.get("replace_requirements") or {}).values()))
    return found


def walk_requirements(reqs):
    for r in reqs:
        yield r
        for opt in r.get("options", []) or []:
            yield from walk_requirements([opt])


def certificate_links(kb: dict, cert_id: str) -> list:
    """Programmes whose requirements explicitly accept this certificate."""
    out = []
    for p in kb["programmes"]:
        for r in walk_requirements(p.get("requirements", [])):
            if r.get("type") == "certificate" and cert_id in r.get("certificates", []):
                out.append(p)
                break
    return out


def progression_edges(kb: dict) -> list:
    ids = {p["id"] for p in kb["programmes"]}
    return [(p["id"], t) for p in kb["programmes"] for t in p.get("progression_to", []) if t in ids]


# ----------------------------------------------------------------- validation
def _validate_source(src, errors, where):
    if not isinstance(src, dict):
        errors.append(f"{where}: 'source' must be an object")
        return
    status = src.get("verification_status")
    if status not in VERIFICATION_STATUSES:
        errors.append(f"{where}: verification_status must be one of {VERIFICATION_STATUSES}")
    if status == "Verified" and (not src.get("url") or not src.get("verified_on")):
        errors.append(f"{where}: 'Verified' requires both an official url and a verified_on date")


def validate_requirement(req, errors, where, seen_ids):
    if not isinstance(req, dict):
        errors.append(f"{where}: requirement must be an object")
        return
    rid, rtype = req.get("id"), req.get("type")
    if not rid:
        errors.append(f"{where}: requirement missing 'id'")
    elif rid in seen_ids:
        errors.append(f"{where}: duplicate requirement id '{rid}'")
    else:
        seen_ids.add(rid)
    if rtype not in REQ_TYPES:
        errors.append(f"{where}/{rid}: unknown type '{rtype}'")
        return
    need = {"min_overall": ["min"], "min_class10": ["min"], "min_subject": ["subject", "min"],
            "subject_studied": ["subject"], "stream_in": ["values"], "entrance": ["exams"],
            "qualification": ["level"], "certificate": ["certificates"], "any_of": ["options"]}[rtype]
    for key in need:
        if key not in req:
            errors.append(f"{where}/{rid}: type '{rtype}' needs '{key}'")
    if "min" in req and not isinstance(req["min"], (int, float)):
        errors.append(f"{where}/{rid}: 'min' must be a number")
    if "min" in req and isinstance(req["min"], (int, float)) and not 0 <= req["min"] <= 100:
        errors.append(f"{where}/{rid}: 'min' must be between 0 and 100")
    if rtype == "qualification" and req.get("level") not in ("bachelor", "diploma"):
        errors.append(f"{where}/{rid}: level must be 'bachelor' or 'diploma'")
    if rtype == "any_of":
        for i, opt in enumerate(req.get("options", [])):
            validate_requirement(opt, errors, f"{where}/{rid}[{i}]", set())


def validate_programme(p: dict) -> list:
    errors = []
    if not isinstance(p, dict):
        return ["programme must be a JSON object"]
    for key in ["id", "name", "level", "field", "requirements", "source"]:
        if key not in p or p[key] in ("", None):
            errors.append(f"missing required key '{key}'")
    if errors:
        return errors
    if not ID_RE.match(str(p["id"])):
        return ["id may contain only letters, digits and underscores"]
    if p["level"] not in LEVELS:
        errors.append(f"level must be one of {LEVELS}")
    if not isinstance(p["requirements"], list) or not p["requirements"]:
        errors.append("requirements must be a non-empty list")
    else:
        seen = set()
        for r in p["requirements"]:
            validate_requirement(r, errors, p["id"], seen)
    _validate_source(p["source"], errors, p["id"])
    if not isinstance(p.get("rule_version", 1), int) or p.get("rule_version", 1) < 1:
        errors.append("rule_version must be a positive integer")
    return errors


def validate_certificate(c: dict) -> list:
    errors = []
    for key in ["id", "name", "issuer", "category", "evidence_source", "verification_status"]:
        if not c.get(key):
            errors.append(f"missing required key '{key}'")
    if c.get("id") and not ID_RE.match(str(c["id"])):
        errors.append("id may contain only letters, digits and underscores")
    if c.get("category") not in CERT_CATEGORIES:
        errors.append(f"category must be one of {CERT_CATEGORIES}")
    if c.get("verification_status") not in VERIFICATION_STATUSES:
        errors.append(f"verification_status must be one of {VERIFICATION_STATUSES}")
    if c.get("verification_status") == "Verified" and not (c.get("url") and c.get("verified_on")):
        errors.append("'Verified' requires both an official url and a verified_on date")
    if "impact" in c and not isinstance(c["impact"], dict):
        errors.append("impact must be an object")
    return errors


def validate_route(r: dict, kb: dict) -> list:
    errors = []
    for key in ["id", "name", "alternative_for", "final_programme", "steps", "source"]:
        if key not in r or r[key] in ("", None):
            errors.append(f"missing required key '{key}'")
    if errors:
        return errors
    if not ID_RE.match(str(r["id"])):
        return ["id may contain only letters, digits and underscores"]
    ids = {p["id"] for p in kb["programmes"]}
    cids = {c["id"] for c in kb["certificates"]}
    for t in list(r["alternative_for"]) + [r["final_programme"]]:
        if t not in ids:
            errors.append(f"unknown programme id '{t}'")
    for s in r["steps"]:
        if s.get("kind") == "programme" and s.get("programme_id") not in ids:
            errors.append(f"step references unknown programme '{s.get('programme_id')}'")
        if s.get("kind") == "certificate" and s.get("certificate_id") not in cids:
            errors.append(f"step references unknown certificate '{s.get('certificate_id')}'")
    if r.get("entry_programme") and r["entry_programme"] not in ids:
        errors.append(f"unknown entry_programme '{r['entry_programme']}'")
    if r.get("officially_recognised", "Unverified") not in RECOGNISED_VALUES:
        errors.append(f"officially_recognised must be one of {RECOGNISED_VALUES}")
    if r.get("officially_recognised") == "Verified - recognised" and r["source"].get("verification_status") != "Verified":
        errors.append("a route cannot be 'Verified - recognised' unless its source is 'Verified'")
    _validate_source(r["source"], errors, r["id"])
    for req in r.get("entry_requirements", []) or []:
        validate_requirement(req, errors, r["id"], set())
    return errors


def validate_kb(kb: dict) -> list:
    errors = []
    for p in kb["programmes"]:
        errors += [f"programme {p.get('id')}: {e}" for e in validate_programme(p)]
    for c in kb["certificates"]:
        errors += [f"certificate {c.get('id')}: {e}" for e in validate_certificate(c)]
    for r in kb["routes"]:
        errors += [f"route {r.get('id')}: {e}" for e in validate_route(r, kb)]
    return errors
