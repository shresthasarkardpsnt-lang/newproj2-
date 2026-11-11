import pytest
from conftest import make_profile
from engine.eligibility import evaluate_programme, evaluate_all
from engine.kb import prog_by_id
from engine.logic import Tri
from engine.validation import validate_profile


def ev(kb, pid, profile):
    return evaluate_programme(profile, prog_by_id(kb, pid))


def cond(res, rid):
    return next(c for c in res.conditions if c.req_id == rid)


def test_normal_eligible(kb, strong):
    r = ev(kb, "btech_cse", strong)
    assert r.decision == "Eligible" and not r.failed and not r.unknown


def test_brief_example_not_eligible_with_exact_gaps(kb, weak):
    r = ev(kb, "btech_cse", weak)
    assert r.decision == "Not eligible"
    assert cond(r, "overall").gap == 7 and cond(r, "mathematics_min").gap == 15
    assert cond(r, "physics_min").result is Tri.TRUE and cond(r, "physics_min").gap_text == "Satisfied"


@pytest.mark.parametrize("overall,expected", [(65, Tri.TRUE), (64.9, Tri.FALSE), (65.1, Tri.TRUE)])
def test_boundary_overall(kb, overall, expected):
    assert cond(ev(kb, "btech_cse", make_profile(overall_pct=overall)), "overall").result is expected


def test_boundary_subject_exact_minimum(kb):
    r = ev(kb, "btech_cse", make_profile(marks={"mathematics": 60}))
    assert cond(r, "mathematics_min").result is Tri.TRUE
    r = ev(kb, "btech_cse", make_profile(marks={"mathematics": 59.5}))
    assert cond(r, "mathematics_min").gap == 0.5


def test_missing_information_gives_needs_review_not_guess(kb):
    p = make_profile(marks={"mathematics": None})
    r = ev(kb, "btech_cse", p)
    assert r.decision == "Needs review"
    assert cond(r, "mathematics_min").result is Tri.UNKNOWN
    assert any("Mathematics" in m for m in r.missing_information)


def test_false_dominates_unknown(kb, weak):
    weak["entrance_exams"] = {}
    r = ev(kb, "btech_cse", weak)
    assert r.unknown and r.decision == "Not eligible"


def test_invalid_marks_are_unknown_never_true(kb):
    r = ev(kb, "btech_cse", make_profile(overall_pct=150, marks={"mathematics": -5}))
    assert cond(r, "overall").result is Tri.UNKNOWN and cond(r, "mathematics_min").result is Tri.UNKNOWN
    errors, _ = validate_profile(make_profile(overall_pct=150, marks={"mathematics": "abc"}))
    assert len(errors) == 2


def test_failed_prerequisite_not_studied(kb):
    p = make_profile(studied={"physics": False}, marks={"physics": None})
    r = ev(kb, "btech_cse", p)
    assert cond(r, "physics_min").result is Tri.FALSE and "not studied" in cond(r, "physics_min").explanation.lower()


def test_stream_rule(kb):
    assert cond(ev(kb, "btech_cse", make_profile(stream="Commerce")), "stream").result is Tri.FALSE
    assert cond(ev(kb, "btech_cse", make_profile(stream=None)), "stream").result is Tri.UNKNOWN


def test_any_of_or_logic(kb):
    base = dict(overall_pct=60, stream="Commerce")
    cs_only = make_profile(**base, studied={"mathematics": False, "computer_science": True}, marks={"mathematics": None, "computer_science": 70})
    assert ev(kb, "bca", cs_only).decision == "Eligible"
    neither = make_profile(**base, studied={"mathematics": False, "computer_science": False}, marks={"mathematics": None, "computer_science": None})
    assert ev(kb, "bca", neither).decision == "Not eligible"
    unknown = make_profile(**base, studied={"mathematics": False, "computer_science": None}, marks={"mathematics": None, "computer_science": None})
    assert ev(kb, "bca", unknown).decision == "Needs review"


@pytest.mark.parametrize("status,expected", [("Qualified", "Eligible"), ("Not taken", "Not eligible"),
                                              ("Appeared - result awaited", "Needs review"), (None, "Needs review")])
def test_entrance_statuses(kb, status, expected):
    p = make_profile(entrance_exams={"JEE Main": {"status": status}})
    assert ev(kb, "btech_cse", p).decision == expected


def test_qualification_rules(kb):
    lat = lambda **d: make_profile(diploma={"has": True, "branch": "Computer Engineering", "pct": 60, **d})
    assert ev(kb, "btech_lateral_cse", lat()).decision == "Eligible"
    assert ev(kb, "btech_lateral_cse", lat(pct=54)).decision == "Not eligible"
    assert ev(kb, "btech_lateral_cse", lat(branch="Civil")).decision == "Not eligible"
    assert ev(kb, "btech_lateral_cse", make_profile(diploma={"has": None})).decision == "Needs review"


def test_certificate_rule_accepts_named_bridge(kb):
    base = dict(bachelor={"has": True, "discipline": "Commerce", "pct": 60}, studied={"mathematics": False}, marks={"mathematics": None},
                entrance_exams={"NIMCET": {"status": "Qualified", "score": 80}})
    assert ev(kb, "mca", make_profile(**base)).decision == "Not eligible"
    assert ev(kb, "mca", make_profile(**base, certificates=["math_bridge_univ"])).decision == "Eligible"


def test_input_profile_not_mutated(kb, weak):
    import copy
    before = copy.deepcopy(weak)
    evaluate_all(weak, kb)
    assert weak == before
