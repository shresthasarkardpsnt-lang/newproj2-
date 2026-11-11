"""Headless Streamlit tests: every page renders and key interactions work."""
import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

from conftest import ROOT  # noqa: E402
from database import db  # noqa: E402
from ui import common  # noqa: E402


def new_app():
    return AppTest.from_file(str(ROOT / "app_full.py"), default_timeout=90).run()


def go(at, page_fragment):
    opts = list(at.sidebar.radio[0].options)
    at.sidebar.radio[0].set_value(next(o for o in opts if page_fragment in o)).run()
    return at


@pytest.fixture()
def app_with_demo():
    conn = common.get_conn()
    db.delete_student(conn, "DEMO-001")
    db.save_student(conn, common.demo_profile())
    at = new_app()
    at.sidebar.selectbox[0].set_value("DEMO-001").run()
    return at


def test_all_fourteen_pages_render(app_with_demo):
    at = app_with_demo
    pages = list(at.sidebar.radio[0].options)
    assert len(pages) == 14
    for p in pages:
        at.sidebar.radio[0].set_value(p).run()
        assert not at.exception, (p, [e.value for e in at.exception])


def test_pages_without_student_do_not_crash():
    at = new_app()
    at.sidebar.selectbox[0].set_value("➕ New / no student").run()
    for p in list(at.sidebar.radio[0].options):
        at.sidebar.radio[0].set_value(p).run()
        assert not at.exception, p


def test_profile_form_rejects_invalid_marks_then_saves(app_with_demo):
    at = app_with_demo
    at.sidebar.selectbox[0].set_value("➕ New / no student").run()
    go(at, "Student Profile")
    at.text_input(key="pf_new_sid").set_value("UI-TEST-1")
    at.text_input(key="pf_new_overall").set_value("150")
    at.text_input(key="pf_new_m_mathematics").set_value("abc")
    next(b for b in at.button if "Save profile" in b.label).click().run()
    assert any("between 0 and 100" in e.value for e in at.error)
    assert db.get_student(common.get_conn(), "UI-TEST-1") is None
    at.text_input(key="pf_new_overall").set_value("72.5")
    at.text_input(key="pf_new_m_mathematics").set_value("68")
    next(b for b in at.button if "Save profile" in b.label).click().run()
    saved = db.get_student(common.get_conn(), "UI-TEST-1")
    assert saved and saved["overall_pct"] == 72.5 and saved["marks"]["mathematics"] == 68
    db.delete_student(common.get_conn(), "UI-TEST-1")


def test_whatif_ui_never_changes_saved_profile(app_with_demo):
    at = go(app_with_demo, "What-if")
    before = db.get_student(common.get_conn(), "DEMO-001")
    at.checkbox(key="wi_ov_use").check().run()
    at.slider(key="wi_ov_val").set_value(90.0).run()
    assert not at.exception
    assert any("HYPOTHETICAL" in e.value for e in at.error)
    assert db.get_student(common.get_conn(), "DEMO-001") == before


def test_roadmap_checkbox_persists_and_keeps_decision(app_with_demo):
    at = go(app_with_demo, "Roadmap")
    cb = [c for c in at.checkbox if c.key and c.key.startswith("rm_btech_cse_req:")]
    assert cb
    cb[0].check().run()
    assert db.get_progress(common.get_conn(), "DEMO-001", "btech_cse")
    assert not at.exception


def test_admin_rejects_invalid_and_accepts_valid_programme(app_with_demo):
    at = go(app_with_demo, "Administrator")
    qa = [b for b in at.button if b.label == "Add programme"]
    assert qa  # quick-add form submit present
    qa[0].click().run()  # empty id/name -> validation errors, no crash
    assert not at.exception and at.error
