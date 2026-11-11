"""Shared Streamlit helpers (database handle, current student, formatting)."""
from __future__ import annotations
from typing import Optional

import streamlit as st

from database import db
from engine.kb import prog_by_id

DEC_ICON = {"Eligible": "✅ Eligible", "Not eligible": "❌ Not eligible", "Needs review": "❓ Needs review"}
TRI_ICON = {"TRUE": "✅ TRUE", "FALSE": "❌ FALSE", "UNKNOWN": "❓ UNKNOWN"}
STATUS_ICON = {"Passed": "✅ Passed", "Failed": "❌ Failed", "Unknown": "❓ Unknown"}
SAMPLE_NOTICE = ("⚠️ Sample admission criteria in this application are **illustrative** and are not official university "
                 "requirements. Always confirm with the institution.")


@st.cache_resource(show_spinner=False)
def get_conn():
    return db.connect()


def get_kb() -> dict:
    return db.load_kb(get_conn())


def select_student(student_id: Optional[str]) -> None:
    """Ask the sidebar selector to switch student on the next run (call before st.rerun())."""
    st.session_state["_select_student"] = student_id
    st.session_state["student_id"] = student_id


def current_student_id() -> Optional[str]:
    return st.session_state.get("student_id")


def current_profile() -> Optional[dict]:
    sid = current_student_id()
    return db.get_student(get_conn(), sid) if sid else None


def require_profile() -> dict:
    profile = current_profile()
    if profile is None:
        st.info("No student is selected. Open **Student Profile** from the sidebar to create or load one.")
        st.stop()
    return profile


def sample_notice(kb: Optional[dict] = None) -> None:
    st.warning(SAMPLE_NOTICE)


def programme_labels(kb: dict) -> dict:
    return {p["id"]: f"{p['name']} ({p['level']})" for p in kb["programmes"]}


def pick_programme(kb: dict, profile: dict, label: str, key: str, default_id: Optional[str] = None) -> str:
    labels = programme_labels(kb)
    ids = list(labels)
    default = default_id or profile.get("preferred_programme")
    idx = ids.index(default) if default in ids else 0
    return st.selectbox(label, ids, index=idx, format_func=lambda i: labels[i], key=key)


def demo_profile() -> dict:
    """Clearly marked sample student used for demonstrations only."""
    return {"student_id": "DEMO-001", "name": "Demo Student (sample data)", "class10_pct": 78, "class12_pct": 58,
            "stream": "Science (PCM)", "overall_pct": 58,
            "marks": {"mathematics": 45, "physics": 65, "chemistry": 60, "biology": None, "computer_science": None, "english": 70},
            "studied": {"mathematics": True, "physics": True, "chemistry": True, "biology": False, "computer_science": None, "english": True},
            "other_subjects": {},
            "entrance_exams": {"State CET": {"status": "Not taken", "score": None}},
            "diploma": {"has": False, "branch": None, "pct": None},
            "bachelor": {"has": False, "degree": "", "discipline": None, "pct": None},
            "additional_qualifications": [], "certificates": [],
            "preferred_programme": "btech_cse", "career_interests": ["Software development", "Artificial intelligence"]}
