"""Reproducible evaluation harness: rule engine vs. a simple if/else baseline.

Ground truth comes from an INDEPENDENT reference implementation (`reference_eligible`) applied to fully
specified synthetic profiles generated with a fixed random seed. Results are measured, never hard-coded.
"""
from __future__ import annotations
import copy
import random
import statistics
import time
from collections import defaultdict
from typing import Optional

from .constants import (CORE_SUBJECTS, ELIGIBLE, NEEDS_REVIEW, STREAMS, DISCIPLINES, DIPLOMA_BRANCHES)
from .eligibility import evaluate_all, evaluate_programme
from .explain import explanation_completeness
from .kb import all_exams, cert_names
from .logic import Tri
from .validation import default_profile

# "Fully specified" profiles use only decisive entrance statuses; pending results are UNKNOWN by design.
STATUSES = ["Not taken", "Qualified"]


def _thresholds(kb) -> list:
    from .kb import walk_requirements
    vals = set()
    for p in kb["programmes"]:
        for r in walk_requirements(p["requirements"]):
            if "min" in r:
                vals.add(float(r["min"]))
            if "min_pct" in r:
                vals.add(float(r["min_pct"]))
    return sorted(vals)


def generate_profiles(kb: dict, n: int = 300, seed: int = 42) -> list:
    """Fully specified (no missing values) synthetic profiles; ~30% of numeric values sit on/near a threshold."""
    rng = random.Random(seed)
    thr = _thresholds(kb) or [50.0]
    exams = all_exams(kb)
    cert_ids = [c["id"] for c in kb["certificates"]]

    def pct():
        if rng.random() < 0.30:
            return max(0.0, min(100.0, rng.choice(thr) + rng.choice([-1.0, -0.5, 0.0, 0.0, 0.5, 1.0])))
        return round(rng.uniform(30, 98), 1)
    out = []
    for i in range(n):
        p = default_profile(f"SYN-{seed}-{i:04d}")
        p["class10_pct"], p["class12_pct"], p["overall_pct"] = pct(), pct(), pct()
        p["stream"] = rng.choice(STREAMS)
        for s in CORE_SUBJECTS:
            skip = 0.3 if s in ("computer_science", "biology", "chemistry") else 0.12 if s in ("mathematics", "physics") else 0.0
            if rng.random() < skip:
                p["studied"][s], p["marks"][s] = False, None
            else:
                p["studied"][s], p["marks"][s] = True, pct()
        p["entrance_exams"] = {e: {"status": rng.choice(STATUSES), "score": round(rng.uniform(20, 99), 1)} for e in exams}
        has_d = rng.random() < 0.4
        p["diploma"] = {"has": has_d, "branch": rng.choice(DIPLOMA_BRANCHES) if has_d else None, "pct": pct() if has_d else None}
        has_b = rng.random() < 0.4
        p["bachelor"] = {"has": has_b, "degree": "", "discipline": rng.choice(DISCIPLINES) if has_b else None,
                         "pct": pct() if has_b else None}
        p["certificates"] = [c for c in cert_ids if rng.random() < 0.15]
        out.append(p)
    return out


def mask_profile(profile: dict, rng: random.Random, p_missing: float = 0.25) -> dict:
    """Blank random fields to simulate incomplete information (never changes the hidden truth profile)."""
    q = copy.deepcopy(profile)
    for key in ("class10_pct", "class12_pct", "overall_pct", "stream"):
        if rng.random() < p_missing:
            q[key] = None
    for s in CORE_SUBJECTS:
        if rng.random() < p_missing:
            q["marks"][s], q["studied"][s] = None, None
    for e in q["entrance_exams"].values():
        if rng.random() < p_missing:
            e["status"] = None
    for key, sub in (("diploma", ("has", "pct", "branch")), ("bachelor", ("has", "pct", "discipline"))):
        for f in sub:
            if rng.random() < p_missing:
                q[key][f] = None
    return q


# ------------------------------------------------------------- independent reference (ground truth)
def reference_eligible(p: dict, prog: dict) -> bool:
    """Straight-line boolean implementation for COMPLETE profiles (written independently of the engine)."""
    def met(r) -> bool:
        t = r["type"]
        if t == "min_overall":
            return p["overall_pct"] >= r["min"]
        if t == "min_class10":
            return p["class10_pct"] >= r["min"]
        if t == "min_subject":
            return bool(p["studied"][r["subject"]]) and p["marks"][r["subject"]] is not None and p["marks"][r["subject"]] >= r["min"]
        if t == "subject_studied":
            return bool(p["studied"][r["subject"]])
        if t == "stream_in":
            return p["stream"] in r["values"]
        if t == "entrance":
            for ex in r["exams"]:
                d = p["entrance_exams"][ex]
                if d["status"] == "Qualified" and (r.get("min_score") is None or d["score"] >= r["min_score"]):
                    return True
            return False
        if t == "qualification":
            d = p[r["level"]]
            if not d["has"]:
                return False
            if r.get("min_pct") is not None and not d["pct"] >= r["min_pct"]:
                return False
            if r.get("disciplines"):
                val = d["discipline"] if r["level"] == "bachelor" else d["branch"]
                return val in r["disciplines"]
            return True
        if t == "certificate":
            return any(c in p["certificates"] for c in r["certificates"])
        if t == "any_of":
            return any(met(o) for o in r["options"])
        raise ValueError(t)
    return all(met(r) for r in prog["requirements"])


def baseline_eligible(p: dict, prog: dict) -> bool:
    """Naive if/else baseline: only overall %, subject minimums and stream; ignores entrance exams,
    qualifications, certificates, 'studied' flags and OR-groups; missing values are treated as 0."""
    ov = p.get("overall_pct") or 0
    for r in prog["requirements"]:
        if r["type"] == "min_overall" and ov < r["min"]:
            return False
        if r["type"] == "min_subject" and (p["marks"].get(r["subject"]) or 0) < r["min"]:
            return False
        if r["type"] == "stream_in" and p.get("stream") not in r["values"]:
            return False
    return True


# ------------------------------------------------------------- metrics
def prf(tp, fp, fn, tn) -> dict:
    total = tp + fp + fn + tn
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    return {"accuracy": (tp + tn) / total if total else 0.0, "precision": prec, "recall": rec,
            "f1": (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0, "tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": total}


def run_suite(kb: dict, n_profiles: int = 300, seed: int = 42, p_missing: float = 0.25) -> dict:
    names = cert_names(kb)
    full = generate_profiles(kb, n_profiles, seed)
    rng = random.Random(seed + 1)
    conf = {"engine": [0, 0, 0, 0], "baseline": [0, 0, 0, 0]}
    needs_review_on_complete = 0
    outcomes = defaultdict(set)          # (prog, req_id) -> {TRUE, FALSE, UNKNOWN}
    completeness = []
    # --- complete profiles
    for p in full:
        for prog in kb["programmes"]:
            truth = reference_eligible(p, prog)
            res = evaluate_programme(p, prog, names)
            if res.decision == NEEDS_REVIEW:
                needs_review_on_complete += 1
            for name, pred in (("engine", res.decision == ELIGIBLE), ("baseline", baseline_eligible(p, prog))):
                # index map: 0=tp 1=fn 2=fp 3=tn
                conf[name][{(True, True): 0, (False, True): 1, (True, False): 2, (False, False): 3}[(pred, truth)]] += 1
            for c in res.conditions:
                outcomes[(prog["id"], c.req_id)].add(c.result.value)
            completeness.append(explanation_completeness(res)[0])
    # --- incomplete profiles
    inc = {"engine_definite": 0, "engine_needs_review": 0, "engine_wrong_definite": 0, "engine_false_eligible": 0,
           "baseline_wrong": 0, "baseline_false_eligible": 0, "pairs": 0}
    for p in full:
        masked = mask_profile(p, rng, p_missing)
        for prog in kb["programmes"]:
            truth = reference_eligible(p, prog)
            res = evaluate_programme(masked, prog, names)
            inc["pairs"] += 1
            if res.decision == NEEDS_REVIEW:
                inc["engine_needs_review"] += 1
            else:
                inc["engine_definite"] += 1
                pred = res.decision == ELIGIBLE
                if pred != truth:
                    inc["engine_wrong_definite"] += 1
                    if pred and not truth:
                        inc["engine_false_eligible"] += 1
            bpred = baseline_eligible(masked, prog)
            if bpred != truth:
                inc["baseline_wrong"] += 1
                if bpred and not truth:
                    inc["baseline_false_eligible"] += 1
            for c in res.conditions:
                outcomes[(prog["id"], c.req_id)].add(c.result.value)
            completeness.append(explanation_completeness(res)[0])
    # --- rule coverage
    total_rules = sum(len(evaluate_programme(default_profile(), p).conditions) for p in kb["programmes"])
    seen_rules = len(outcomes)
    both = sum(1 for v in outcomes.values() if "TRUE" in v and "FALSE" in v)
    cov_rows = [{"programme": k[0], "rule": k[1], "outcomes_seen": ", ".join(sorted(v))} for k, v in sorted(outcomes.items())]
    # --- timing (complete profiles; per programme evaluation and per full-KB evaluation)
    per_prog, per_profile = [], []
    for p in full[:100]:
        t0 = time.perf_counter()
        for prog in kb["programmes"]:
            t1 = time.perf_counter()
            evaluate_programme(p, prog, names)
            per_prog.append((time.perf_counter() - t1) * 1000)
        per_profile.append((time.perf_counter() - t0) * 1000)
    per_prog.sort()
    tp, fn, fp, tn = conf["engine"]
    btp, bfn, bfp, btn = conf["baseline"]
    return {
        "config": {"n_profiles": n_profiles, "seed": seed, "p_missing": p_missing, "programmes": len(kb["programmes"]),
                   "pairs_complete": n_profiles * len(kb["programmes"])},
        "engine": prf(tp, fp, fn, tn), "baseline": prf(btp, bfp, bfn, btn),
        "engine_needs_review_on_complete": needs_review_on_complete,
        "incomplete": {**inc, "engine_decision_rate": inc["engine_definite"] / inc["pairs"],
                       "baseline_accuracy_vs_truth": 1 - inc["baseline_wrong"] / inc["pairs"],
                       "engine_definite_accuracy": (1 - inc["engine_wrong_definite"] / inc["engine_definite"]) if inc["engine_definite"] else 1.0},
        "rule_coverage": {"rules_total": total_rules, "rules_exercised": seen_rules, "rules_with_true_and_false": both,
                          "exercised_ratio": seen_rules / total_rules if total_rules else 0.0,
                          "both_outcomes_ratio": both / total_rules if total_rules else 0.0, "rows": cov_rows},
        "explanation_completeness": {"mean": statistics.mean(completeness), "min": min(completeness), "n": len(completeness)},
        "timing_ms": {"mean_per_programme": statistics.mean(per_prog), "p95_per_programme": per_prog[int(0.95 * (len(per_prog) - 1))],
                      "mean_per_student_all_programmes": statistics.mean(per_profile)},
        "notes": ["Ground truth = independent reference implementation on synthetic profiles (seeded). Not real student data.",
                  "Timing depends on the machine and is the only non-deterministic figure."],
    }
