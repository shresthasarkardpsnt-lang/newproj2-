import pandas as pd
import streamlit as st

from engine.constants import LEVELS
from engine.higher import analyse_higher
from engine.reports import to_csv_bytes
from . import common


def render():
    st.title("📈 Higher Eligibility Opportunities")
    kb = common.get_kb()
    profile = common.require_profile()
    common.sample_notice(kb)
    c1, c2 = st.columns(2)
    level = c1.selectbox("Level", ["All"] + LEVELS)
    field = c2.selectbox("Field", ["All"] + sorted({p["field"] for p in kb["programmes"]}))
    h = analyse_higher(profile, kb, level, field)
    st.info(h["disclaimer"])
    st.caption(f"Reference threshold: {h['reference'] if h['reference'] is not None else 'n/a'}% "
               f"({h['reference_basis']}). 'Higher' means a larger overall-percentage minimum than this reference.")

    t1, t2 = st.tabs([f"Currently eligible ({len(h['eligible'])})", f"Higher thresholds ({len(h['higher'])})"])
    with t1:
        if h["eligible"]:
            st.dataframe(pd.DataFrame(h["eligible"])[["Programme", "Level", "Field", "Min overall %", "Subject minimums", "Entrance exams"]], hide_index=True)
        else:
            st.write("No programmes are currently fully eligible for the selected filters.")
    with t2:
        if not h["higher"]:
            st.write("No higher-threshold programmes found for the selected filters.")
        else:
            df = pd.DataFrame(h["higher"])
            st.dataframe(df[["Programme", "Level", "Min overall %", "Threshold vs reference", "Subject minimums",
                              "Entrance exams", "Total marks gap", "Failed", "Unknown"]], hide_index=True)
            own = profile.get("overall_pct")
            if own is not None:
                chart = pd.DataFrame({"Required overall %": df["Min overall %"], "Your overall %": own}).set_axis(df["Programme"].tolist())
                st.markdown("**Overall percentage: required vs yours**")
                st.bar_chart(chart)
            pick = st.selectbox("What would it take to qualify?", df["Programme"].tolist())
            row = df[df["Programme"] == pick].iloc[0]
            st.markdown(f"**{pick}**")
            st.write(row["What is needed"])
            st.write(f"Entrance examinations: {row['Entrance exams']}")
            st.caption("Marks gaps are measured against illustrative sample thresholds. Entrance requirements may add further conditions.")
            st.download_button("⬇️ Download CSV", to_csv_bytes(df.drop(columns=["programme_id"])), "higher_opportunities.csv", "text/csv")
