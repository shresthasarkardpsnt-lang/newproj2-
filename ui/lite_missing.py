"""What is missing: one 4-column table plus plain next steps."""
import pandas as pd
import streamlit as st

from engine.eligibility import evaluate_all
from engine.logic import Tri
from engine.missing import analyse
from . import common


def gap_label(c) -> str:
    if c.result is Tri.TRUE:
        return "✅ Met"
    if c.result is Tri.UNKNOWN:
        return "❓ Information needed"
    return "❌ " + c.gap_text.replace(" percentage points", " points short")


def render():
    st.title("🔍 What's Missing")
    kb = common.get_kb()
    profile = common.require_profile()
    results = evaluate_all(profile, kb)
    pref = profile.get("preferred_programme")
    default = pref or next((r.programme_id for r in results if r.decision != "Eligible"), results[0].programme_id)
    pid = common.pick_programme(kb, profile, "Programme", "lite_missing_prog", default_id=default)
    r = next(x for x in results if x.programme_id == pid)
    a = analyse(r)
    st.markdown(f"### {common.DEC_ICON[r.decision]}")
    st.write(r.final_explanation)
    st.dataframe(pd.DataFrame([{"Requirement": c.label, "Your marks": c.student_value, "Required": c.required, "Gap": gap_label(c)}
                               for c in r.conditions]), hide_index=True)
    if a["information_required"]:
        st.markdown("**Please add to your profile:**")
        for m in a["information_required"]:
            st.markdown(f"- {m}")
    if a["next_steps"]:
        st.markdown("**What you can do:**")
        for s in dict.fromkeys(a["next_steps"]):
            st.markdown(f"- {s}")
        st.caption("Suggestions only. They do not guarantee eligibility or admission.")
    elif r.decision == "Eligible":
        st.success("Nothing is missing for this programme.")
