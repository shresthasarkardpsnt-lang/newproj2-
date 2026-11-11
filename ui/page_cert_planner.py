import pandas as pd
import streamlit as st

from database import db
from engine.certificates import NO_PROBABILITY, knowledge_gaps, recommend
from engine.constants import CAREER_INTERESTS, CERT_CATEGORIES
from engine.reports import to_csv_bytes
from . import common


def render():
    st.title("📚 Certificate & Skill Improvement Planner")
    kb, conn = common.get_kb(), common.get_conn()
    profile = common.require_profile()
    common.sample_notice(kb)
    st.info("A certificate never changes your marks or formal eligibility by itself. It matters for admission only if the "
            "institution's rule explicitly accepts it. " + NO_PROBABILITY)
    pid = common.pick_programme(kb, profile, "Target programme", "cert_target")
    interests = st.multiselect("Career interests (used for matching only)", CAREER_INTERESTS, default=profile.get("career_interests", []))
    work = {**profile, "career_interests": interests}

    gaps = knowledge_gaps(work, kb, pid)
    if gaps:
        st.markdown("**Knowledge gaps detected**")
        for g in gaps:
            st.markdown(f"- **{g['area'].replace('_', ' ').title()}**: " + "; ".join(g["reasons"]))
    tname = next(p["name"] for p in kb["programmes"] if p["id"] == pid)
    recs = recommend(work, kb, pid, include_completed=True)
    if not recs:
        st.info("No matching certificates found for this target and profile.")
        return
    st.download_button("⬇️ Recommendations CSV", to_csv_bytes(pd.DataFrame([{
        "Certificate": r["name"], "Issuer": r["issuer"], "Category": r["category"], "Match strength": r["relevance"],
        "Skills": ", ".join(r["skills"]), "Duration": r["duration_display"], "Cost": r["cost_display"], "URL": r["url"] or "",
        "Recognition": r["recognition_status"], "Evidence": r["evidence_source"], "Verification": r["verification_status"]} for r in recs])),
        "certificate_recommendations.csv", "text/csv")
    tabs = st.tabs([f"{c.split()[0]} {' '.join(c.split()[1:3])}" for c in CERT_CATEGORIES])
    for tab, cat in zip(tabs, CERT_CATEGORIES):
        with tab:
            st.caption(cat)
            items = [r for r in recs if r["category"] == cat]
            if not items:
                st.write("No recommendations in this category.")
            for r in items:
                f = r["flags"]
                with st.expander(f"{'✔️ ' if r['completed'] else ''}{r['name']}  -  {r['issuer']}  (match: {r['relevance']})"):
                    st.markdown("**Why recommended:** " + " ".join(r["reasons"]))
                    st.markdown(f"**Skills covered:** {', '.join(r['skills'])}")
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**Duration:** {r['duration_display']}")
                    c2.markdown(f"**Cost:** {r['cost_display']}")
                    st.markdown(f"**Official URL:** {r['url'] or 'none stored'}" + (" (issuer home page; confirm the exact course page)" if r["url"] else ""))
                    st.markdown(f"**Recognition status:** {r['recognition_status']}")
                    st.caption(f"Evidence source: {r['evidence_source']} | Verification: {r['verification_status']} | Verified on: {r['verified_on'] or 'not verified'}")
                    st.markdown("**Effect of this certificate**")
                    st.markdown(f"- Improves formal admission eligibility for **{tname}**: "
                                f"{'✅ Yes (named in the sample rule)' if f['improves_target_eligibility'] else '❌ No'}")
                    if f["improves_formal_eligibility"] and not f["improves_target_eligibility"]:
                        st.markdown(f"  - It is named in rules of other programmes: {', '.join(f['formal_programmes'])}")
                    st.markdown(f"- Improves academic preparation: {'✅ Yes' if f['improves_academic_preparation'] else '➖ Not primarily'}")
                    st.markdown(f"- Strengthens skills / profile: {'✅ Yes' if f['strengthens_profile'] else '➖ Not primarily'}")
                    st.markdown(f"- Admission recognition unverified: {'⚠️ Yes' if f['admission_recognition_unverified'] else 'No'}")
                    done = st.checkbox("I have completed this", value=r["completed"], key=f"cp_{r['id']}")
                    if done != r["completed"]:
                        db.set_certificate_completed(conn, profile["student_id"], r["id"], done)
                        st.rerun()
