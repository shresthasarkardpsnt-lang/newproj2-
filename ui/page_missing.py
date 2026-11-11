import pandas as pd
import streamlit as st

from engine.eligibility import evaluate_all
from engine.missing import analyse
from engine.reports import gap_pdf, to_csv_bytes
from . import common


def render():
    st.title("🔍 Missing Conditions & Marks Gap Analyzer")
    st.caption("Shows exactly which conditions you meet, which you miss, by how much, and what information is still needed.")
    kb = common.get_kb()
    profile = common.require_profile()
    common.sample_notice(kb)
    results = evaluate_all(profile, kb)
    pref = profile.get("preferred_programme")
    first_not = next((r.programme_id for r in results if r.decision != "Eligible"), None)
    pid = common.pick_programme(kb, profile, "Programme to analyse", "missing_prog", default_id=pref or first_not)
    r = next(x for x in results if x.programme_id == pid)
    a = analyse(r)
    st.markdown(f"### {common.DEC_ICON[r.decision]}: {r.programme_name}")
    st.write(a["summary"])
    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Passed", len(a["passed"]))
    c2.metric("❌ Failed", len(a["failed"]))
    c3.metric("❓ Unknown", len(a["unknown"]))

    df = pd.DataFrame(a["rows"])
    df["Status"] = df["Status"].map(common.STATUS_ICON)
    st.dataframe(df[["Condition", "Student marks", "Required", "Gap", "Status"]], hide_index=True)
    if a["numeric_gaps"]:
        st.markdown("**Marks gaps (percentage points)**")
        st.bar_chart(pd.DataFrame(a["numeric_gaps"], columns=["Condition", "Gap"]).set_index("Condition"))
        st.caption(f"Total numeric gap across failed conditions: {a['total_numeric_gap']:g} percentage points.")

    if a["failed"]:
        st.subheader("❌ Why each failed condition fails")
        for c in a["failed"]:
            with st.expander(c.label, expanded=True):
                st.write(c.explanation)
                st.caption(f"Rule: {c.rule}")
    if a["unknown"]:
        st.subheader("❓ Additional information required")
        for m in a["information_required"]:
            st.markdown(f"- {m}")
    if a["passed"]:
        with st.expander(f"✅ Passed conditions ({len(a['passed'])})"):
            for c in a["passed"]:
                st.markdown(f"- **{c.label}**: {c.explanation}")
    st.subheader("Possible next steps")
    if a["next_steps"]:
        for s in a["next_steps"]:
            st.markdown(f"- {s}")
        st.caption("Next steps are suggestions only. They do not guarantee eligibility or admission.")
    else:
        st.success("All conditions are satisfied under this sample rule.")
    d1, d2 = st.columns(2)
    d1.download_button("⬇️ CSV", to_csv_bytes(pd.DataFrame(a["rows"])), "missing_conditions.csv", "text/csv")
    d2.download_button("⬇️ PDF", gap_pdf(profile, a), "missing_conditions.pdf", "application/pdf")
