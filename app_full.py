"""Academic Pathway Reasoning & Improvement System - Streamlit entry point.

Full 14-page version.  Run with:  streamlit run app_full.py
Deterministic rule-based reasoning only: no external AI services are used.
"""
import streamlit as st

st.set_page_config(page_title="Academic Pathway Reasoning System", page_icon="🎓", layout="wide")

from database import db  # noqa: E402
from ui import (common, page_admin, page_cert_impact, page_cert_planner, page_dashboard, page_evaluation,  # noqa: E402
                page_higher, page_history, page_kb, page_missing, page_profile, page_roadmap, page_routes,
                page_testing, page_whatif)

PAGES = {
    "🏠 Dashboard": page_dashboard,
    "🧑‍🎓 Student Profile": page_profile,
    "📋 Eligibility Evaluation": page_evaluation,
    "🔍 Missing Conditions Analyzer": page_missing,
    "📈 Higher Eligibility Opportunities": page_higher,
    "🧭 Alternative Academic Pathways": page_routes,
    "📚 Certificate Recommendation Planner": page_cert_planner,
    "🧪 Certificate Impact Analysis": page_cert_impact,
    "🎛️ What-if Simulator": page_whatif,
    "🗺️ Academic Improvement Roadmap": page_roadmap,
    "📖 Programme Knowledge Base": page_kb,
    "🕑 Evaluation History": page_history,
    "🛠️ Administrator Dashboard": page_admin,
    "✅ Testing & Performance": page_testing,
}
NONE = "➕ New / no student"


def main():
    conn = common.get_conn()
    students = db.list_students(conn)
    ids = [s["student_id"] for s in students]
    labels = {s["student_id"]: f"{s['student_id']}" + (f" - {s['name']}" if s["name"] else "") for s in students}
    pending = st.session_state.pop("_select_student", "__none__")
    if pending != "__none__":
        st.session_state["active_student"] = pending or NONE
    if st.session_state.get("active_student") not in [NONE] + ids:
        st.session_state["active_student"] = NONE
    with st.sidebar:
        st.markdown("## 🎓 Academic Pathways")
        choice = st.selectbox("Active student", [NONE] + ids, key="active_student",
                              format_func=lambda i: i if i == NONE else labels[i])
        st.session_state["student_id"] = None if choice == NONE else choice
        page = st.radio("Navigate", list(PAGES), key="nav_page")
        st.divider()
        st.caption("Rule-based and explainable. Sample criteria are illustrative, not official.")
    PAGES[page].render()


main()
