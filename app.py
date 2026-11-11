"""Academic Pathway Reasoning System - applicant interface.

Run with:  streamlit run app.py        (the full 14-page version is app_full.py)
Deterministic rule-based reasoning only: no external AI services or network calls.
"""
import streamlit as st

st.set_page_config(page_title="Academic Pathway Finder", page_icon="🎓", layout="wide")

from database import db  # noqa: E402
from ui import common, studio, theme  # noqa: E402

NONE = "➕ New student"
RENDER = {studio.PAGES[0]: studio.page_profile, studio.PAGES[1]: studio.page_programmes, studio.PAGES[2]: studio.page_gaps,
          studio.PAGES[3]: studio.page_reasoning, studio.PAGES[4]: studio.page_quality}


def safe(fn):
    """Show a friendly message instead of an error box. Streamlit's own stop/rerun signals pass through."""
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        if type(exc).__name__ in ("StopException", "RerunException"):
            raise
        st.warning("Something unexpected happened on this page. Your saved data is safe. Try another step or reload.")
        with st.expander("Technical detail"):
            st.code(repr(exc))


def main():
    theme.inject()
    students = db.list_students(common.get_conn())
    ids = [s["student_id"] for s in students]
    labels = {s["student_id"]: s["student_id"] + (f" - {s['name']}" if s["name"] else "") for s in students}
    pending = st.session_state.pop("_select_student", "__none__")
    if pending != "__none__":
        st.session_state["active_student"] = pending or NONE
        st.session_state["nav_page"] = studio.PAGES[1] if pending else studio.PAGES[0]
    if st.session_state.get("active_student") not in [NONE] + ids:
        st.session_state["active_student"] = NONE
    with st.sidebar:
        theme.show("<div class='aps-brand'>🎓 Pathway Finder</div><div class='aps-brandsub'>Know where you stand. See the way in.</div>")
        choice = st.selectbox("Student", [NONE] + ids, key="active_student", format_func=lambda i: i if i == NONE else labels[i])
        st.session_state["student_id"] = None if choice == NONE else choice
        st.caption("Rule-based and explainable. Works offline. Sample criteria are illustrative, not official.")
    if st.session_state.get("nav_page") not in studio.PAGES:
        st.session_state["nav_page"] = studio.PAGES[0]
    page = st.radio("Step", studio.PAGES, key="nav_page", horizontal=True, label_visibility="collapsed")
    safe(RENDER[page])


main()
