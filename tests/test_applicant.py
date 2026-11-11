from conftest import make_profile
from engine import applicant as A
from engine.constants import ELIGIBLE, NEEDS_REVIEW, NOT_ELIGIBLE
from engine.eligibility import evaluate_all


def test_representative_cases_meet_acceptance_criteria(kb):
    rows = A.run_cases(kb)
    kinds = {r["kind"] for r in rows}
    assert kinds == {"Normal", "Edge", "Incomplete"}
    assert all(r["pass"] for r in rows), [r for r in rows if not r["pass"]]


def test_decisions_are_unchanged_by_the_applicant_layer(kb, weak):
    direct = {r.programme_id: r.decision for r in evaluate_all(weak, kb)}
    wrapped = {c["id"]: c["decision"] for c in A.programme_cards(weak, kb)}
    assert direct == wrapped


def test_confidence_and_review_states(kb, strong, weak):
    cards = {c["id"]: c for c in A.programme_cards(strong, kb)}
    assert cards["btech_cse"]["decision"] == ELIGIBLE and cards["btech_cse"]["confidence"]["label"] in ("High", "Medium")
    pending = make_profile(entrance_exams={"JEE Main": {"status": "Appeared - result awaited"}})
    c = {x["id"]: x for x in A.programme_cards(pending, kb)}["btech_cse"]
    assert c["decision"] == NEEDS_REVIEW and c["confidence"]["label"] == "Low" and c["review"]["code"] == "human"
    blank = make_profile(marks={"mathematics": None})
    c = {x["id"]: x for x in A.programme_cards(blank, kb)}["btech_cse"]
    assert c["review"]["code"] == "input"
    w = {x["id"]: x for x in A.programme_cards(weak, kb)}["btech_cse"]
    assert w["decision"] == NOT_ELIGIBLE and w["review"]["code"] in ("auto", "check")


def test_borderline_and_exceptions(kb):
    p = make_profile(overall_pct=65, marks={"mathematics": 60})
    c = {x["id"]: x for x in A.programme_cards(p, kb)}["btech_cse"]
    assert c["decision"] == ELIGIBLE and c["review"]["code"] == "check"
    kinds = [k for k, _ in c["exceptions"]]
    assert "Borderline mark" in kinds and "Not modelled" in kinds and "Unverified rule" in kinds


def test_every_condition_has_a_reasoning_step_with_evidence(kb, weak):
    for c in A.programme_cards(weak, kb):
        steps = A.reasoning_chain(c["result"])
        assert len(steps) == len(c["result"].conditions)
        assert all(s["evidence"] and s["logical_rule"] and s["explanation"] for s in steps)


def test_pathways_and_baseline(kb, weak):
    routes = A.pathways(weak, "btech_cse", kb)
    assert routes and all(r["chain"] and r["disclaimer"] for r in routes)
    cmp_ = A.baseline_comparison(weak, kb)
    assert len(cmp_) == len(kb["programmes"]) and any(not x["agree"] for x in cmp_)
