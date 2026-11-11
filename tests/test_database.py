import copy
from conftest import make_profile
from database import db
from engine.eligibility import evaluate_all


def test_student_crud_and_cert_sync(conn):
    sid = db.save_student(conn, make_profile(student_id="S1", name="Ann"))
    assert db.get_student(conn, sid)["name"] == "Ann"
    db.sync_certificates(conn, sid, ["cs50", "pcep"])
    assert db.get_student(conn, sid)["certificates"] == ["cs50", "pcep"]
    db.sync_certificates(conn, sid, ["cs50"])
    assert db.list_completed_certificates(conn, sid) == ["cs50"]
    p = db.get_student(conn, sid); p["name"] = "Ann B"; db.save_student(conn, p)
    assert db.get_student(conn, sid)["name"] == "Ann B" and len(db.list_students(conn)) == 1
    db.delete_student(conn, sid)
    assert db.get_student(conn, sid) is None


def test_save_requires_id(conn):
    import pytest
    with pytest.raises(ValueError):
        db.save_student(conn, make_profile(student_id="  "))


def test_evaluation_history_and_missing_conditions(conn, kb, weak):
    db.save_student(conn, weak)
    res = evaluate_all(weak, kb)
    run = db.save_evaluation(conn, "T1", weak, res)
    decs = db.run_decisions(conn, run)
    assert len(decs) == len(kb["programmes"])
    assert {d["decision"] for d in decs} <= {"Eligible", "Not eligible", "Needs review"}
    miss = db.run_missing(conn, run)
    assert any(m["condition_label"].startswith("Mathematics") and m["gap"] == 15 for m in miss)
    assert db.list_runs(conn, "T1")[0]["run_id"] == run


def test_roadmap_progress_roundtrip(conn):
    db.set_progress(conn, "S", "btech_cse", "k1", True)
    db.set_progress(conn, "S", "btech_cse", "k2", True)
    db.set_progress(conn, "S", "btech_cse", "k2", False)
    assert db.get_progress(conn, "S", "btech_cse") == {"k1"}


def test_kb_seeded_and_versioned(conn, kb):
    loaded = db.load_kb(conn)
    assert len(loaded["programmes"]) == len(kb["programmes"])
    item = copy.deepcopy(next(p for p in loaded["programmes"] if p["id"] == "bca"))
    item["requirements"][0]["min"] = 55
    ok, v = db.upsert_kb_item(conn, "programmes", item, "raise threshold")
    assert ok and v == 2
    assert [r for r in db.load_kb(conn)["programmes"] if r["id"] == "bca"][0]["requirements"][0]["min"] == 55
    assert len(db.kb_history(conn, "programmes", "bca")) == 2


def test_kb_validation_rejects_bad_items(conn):
    bad = {"id": "x", "name": "X", "level": "UG", "field": "CS", "requirements": [{"id": "o", "type": "min_overall"}],
           "source": {"verification_status": "Verified"}}
    ok, errs = db.upsert_kb_item(conn, "programmes", bad)
    assert not ok and any("needs 'min'" in e for e in errs) and any("Verified" in e for e in errs)
    ok, errs = db.upsert_kb_item(conn, "routes", {"id": "r", "name": "r", "alternative_for": ["nope"], "final_programme": "nope",
                                                   "steps": [], "source": {"verification_status": "Unverified"}})
    assert not ok


def test_kb_delete_and_export(conn, tmp_path):
    assert db.delete_kb_item(conn, "certificates", "pcep")
    assert "pcep" not in [c["id"] for c in db.load_kb(conn)["certificates"]]
    files = db.export_kb_to_json(conn, tmp_path)
    assert len(files) == 3 and all((tmp_path / n).exists() for n in ("programmes.json", "certificates.json", "alternative_routes.json"))
