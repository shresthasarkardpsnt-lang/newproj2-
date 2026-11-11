from conftest import make_profile
from engine.eligibility import evaluate_programme
from engine.higher import analyse_higher
from engine.kb import prog_by_id
from engine.missing import analyse


def test_gap_table_matches_brief(kb, weak):
    a = analyse(evaluate_programme(weak, prog_by_id(kb, "btech_cse")))
    rows = {r["Condition"]: r for r in a["rows"]}
    assert rows["Overall percentage (Class 12 / equivalent)"]["Gap"] == "7 percentage points"
    assert rows["Mathematics marks"]["Gap"] == "15 percentage points"
    assert rows["Physics marks"]["Gap"] == "Satisfied"
    assert a["total_numeric_gap"] == 22 and len(a["failed"]) == 3  # overall, maths, entrance (JEE not taken)


def test_unknown_listed_with_required_info(kb):
    p = make_profile(entrance_exams={})
    a = analyse(evaluate_programme(p, prog_by_id(kb, "btech_cse")))
    assert a["information_required"] and any("JEE Main" in m for m in a["information_required"])


def test_next_steps_never_promise_admission(kb, weak):
    steps = " ".join(analyse(evaluate_programme(weak, prog_by_id(kb, "btech_cse")))["next_steps"]).lower()
    assert "guarantee" not in steps and steps


def test_higher_opportunities(kb, weak):
    h = analyse_higher(weak, kb)
    assert h["reference"] == 55 and h["eligible"]
    names = [r["Programme"] for r in h["higher"]]
    assert "B.Tech Computer Science & Engineering" in names
    gap = next(r for r in h["higher"] if r["Programme"].startswith("B.Tech Computer"))["Total marks gap"]
    assert gap == 22
    assert all(r["Min overall %"] > h["reference"] for r in h["higher"])
    assert "better programme" in h["disclaimer"]
