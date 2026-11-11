import pandas as pd
import streamlit as st

from database import db
from engine.eligibility import evaluate_all
from engine.higher import analyse_higher
from engine.kb import prog_by_id
from engine.roadmap import build_roadmap
from . import common


def render():
    st.title("🎓 Academic Pathway Reasoning & Improvement System")
    st.caption("Deterministic, rule-based and explainable. Every outcome traces back to a stated rule and your own inputs. "
               "Runs fully offline with no external AI services.")
    kb = common.get_kb()
    common.sample_notice(kb)
    profile = common.current_profile()
    if profile is None:
        st.subheader("Get started")
        st.write("Create a student profile, then explore eligibility, gaps, alternative routes and an improvement roadmap.")
        if st.button("Load a demo student (sample data)"):
            sid = db.save_student(common.get_conn(), common.demo_profile())
            common.select_student(sid)
            st.rerun()
        return
    results = evaluate_all(profile, kb)
    st.subheader(f"Overview for {profile.get('name') or profile['student_id']}")
    c1, c2, c3, c4 = st.columns(4)
    n = lambda d: sum(1 for r in results if r.decision == d)
    c1.metric("✅ Eligible", n("Eligible"))
    c2.metric("❌ Not eligible", n("Not eligible"))
    c3.metric("❓ Needs review", n("Needs review"))
    c4.metric("Programmes in knowledge base", len(kb["programmes"]))

    df = pd.DataFrame([{"Level": r.level, "Decision": r.decision} for r in results])
    chart = df.pivot_table(index="Level", columns="Decision", aggfunc=len, fill_value=0)
    st.markdown("**Decisions by programme level**")
    st.bar_chart(chart)

    pid = profile.get("preferred_programme")
    if pid and prog_by_id(kb, pid):
        r = next(x for x in results if x.programme_id == pid)
        st.markdown(f"### Preferred programme: {r.programme_name}")
        st.write(f"**{common.DEC_ICON[r.decision]}** - {r.final_explanation}")
        rm = build_roadmap(profile, kb, pid, db.get_progress(common.get_conn(), profile["student_id"], pid))
        st.progress(rm["progress"], text=f"Roadmap progress: {rm['done']} of {rm['total']} items")
    else:
        st.info("Choose a preferred programme in your profile to see a focused summary and roadmap.")

    h = analyse_higher(profile, kb)
    if h["higher"]:
        st.markdown("**Closest programmes with higher thresholds** (see *Higher Eligibility Opportunities*)")
        st.dataframe(pd.DataFrame(h["higher"][:3])[["Programme", "Min overall %", "Total marks gap", "Entrance exams"]], hide_index=True)
    ver = sum(1 for p in kb["programmes"] if p["source"].get("verification_status") == "Verified")
    st.caption(f"Knowledge base: {len(kb['programmes'])} programmes, {len(kb['certificates'])} certificates, "
               f"{len(kb['routes'])} routes. Verified programme sources: {ver}.")
