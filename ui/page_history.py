import json

import pandas as pd
import streamlit as st

from database import db
from engine.reports import to_csv_bytes
from . import common


def render():
    st.title("🕑 Evaluation History")
    conn = common.get_conn()
    profile = common.require_profile()
    runs = db.list_runs(conn, profile["student_id"])
    if not runs:
        st.info("No saved evaluations yet. Use **Save this evaluation to history** on the Eligibility Evaluation page.")
        return
    st.dataframe(pd.DataFrame(runs).rename(columns={"run_id": "Run", "run_at": "When", "preferred_programme": "Preferred",
                                                     "eligible": "Eligible", "not_eligible": "Not eligible",
                                                     "needs_review": "Needs review", "note": "Note"}), hide_index=True)
    ids = [r["run_id"] for r in runs]
    rid = st.selectbox("Open a run", ids)
    dec = db.run_decisions(conn, rid)
    dfd = pd.DataFrame(dec)[["programme_name", "decision", "passed", "failed", "unknown", "rule_version", "final_explanation"]]
    st.dataframe(dfd.assign(decision=dfd["decision"].map(common.DEC_ICON)), hide_index=True)
    miss = db.run_missing(conn, rid)
    if miss:
        with st.expander(f"Missing / failed conditions recorded ({len(miss)})"):
            st.dataframe(pd.DataFrame(miss).drop(columns=["id", "run_id"]), hide_index=True)
    st.download_button("⬇️ Run decisions CSV", to_csv_bytes(pd.DataFrame(dec)), f"run_{rid}.csv", "text/csv")
    if len(ids) > 1:
        st.subheader("Compare with the previous run")
        older = [i for i in ids if i < rid]
        if older:
            prev = {d["programme_id"]: d["decision"] for d in db.run_decisions(conn, older[0])}
            changes = [{"Programme": d["programme_name"], "Previous": prev.get(d["programme_id"], "-"), "This run": d["decision"]}
                       for d in dec if prev.get(d["programme_id"]) != d["decision"]]
            st.dataframe(pd.DataFrame(changes), hide_index=True) if changes else st.write(f"No decision changes versus run #{older[0]}.")
        else:
            st.write("This is the oldest run.")
