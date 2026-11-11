import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

from conftest import ROOT  # noqa: E402
from database import db  # noqa: E402
from ui import common, studio  # noqa: E402


def app():
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=90).run()


def _demo():
    conn = common.get_conn()
    db.delete_student(conn, "DEMO-001")
    db.save_student(conn, common.demo_profile())


def test_five_pages_render_without_student_and_with_demo():
    at = app()
    assert list(at.radio(key="nav_page").options) == studio.PAGES
    for p in studio.PAGES:
        at.radio(key="nav_page").set_value(p).run()
        assert not at.exception, p
    _demo()
    at = app()
    at.sidebar.selectbox[0].set_value("DEMO-001").run()
    for p in studio.PAGES:
        at.radio(key="nav_page").set_value(p).run()
        assert not at.exception, p


def test_save_new_student_and_reject_bad_input():
    conn = common.get_conn()
    db.delete_student(conn, "LITE-1")
    at = app()
    at.sidebar.selectbox[0].set_value("➕ New student").run()
    at.text_input(key="lp_new_sid").set_value("LITE-1")
    at.text_input(key="lp_new_ov").set_value("120")
    next(b for b in at.button if "Save" in b.label).click().run()
    assert at.error and db.get_student(conn, "LITE-1") is None
    at.text_input(key="lp_new_ov").set_value("70")
    at.text_input(key="lp_new_ma").set_value("65")
    next(b for b in at.button if "Save" in b.label).click().run()
    saved = db.get_student(conn, "LITE-1")
    assert saved and saved["overall_pct"] == 70 and saved["marks"]["mathematics"] == 65
    db.delete_student(conn, "LITE-1")
