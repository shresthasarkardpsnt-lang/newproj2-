import pandas as pd
import streamlit as st

from database import db
from engine.constants import DECISIONS, FIELDS, LEVELS
from engine.eligibility import evaluate_all
from engine.explain import explain_result, explanation_completeness
from engine.reports import conditions_dataframe, evaluation_pdf, results_dataframe, to_csv_bytes
from . import common


def render():
    st.title("📋 Eligibility Evaluation")
    kb, conn = common.get_kb(), common.get_conn()
    profile = common.require_profile()
    common.sample_notice(kb)
    results = evaluate_all(profile, kb)

    c1, c2, c3 = st.columns(3)
    lv = c1.multiselect("Level", LEVELS, default=LEVELS)
    fl = c2.multiselect("Field", sorted({r.field for r in results}), default=sorted({r.field for r in results}))
    dc = c3.multiselect("Decision", DECISIONS, default=DECISIONS)
    shown = [r for r in results if r.level in lv and r.field in fl and r.decision in dc]
    df = results_dataframe(shown)
    if not df.empty:
        df["Decision"] = df["Decision"].map(common.DEC_ICON)
    st.dataframe(df, hide_index=True)

    b1, b2, b3 = st.columns(3)
    b1.download_button("⬇️ Summary CSV", to_csv_bytes(results_dataframe(shown)), "eligibility_summary.csv", "text/csv")
    b2.download_button("⬇️ Detailed CSV", to_csv_bytes(conditions_dataframe(shown)), "eligibility_details.csv", "text/csv")
    b3.download_button("⬇️ PDF report", evaluation_pdf(profile, shown), "eligibility_report.pdf", "application/pdf")
    if st.button("💾 Save this evaluation to history"):
        run = db.save_evaluation(conn, profile["student_id"], profile, results)
        st.success(f"Saved as run #{run}. See Evaluation History.")

    st.divider()
    st.subheader("Explanation for one programme")
    if not shown:
        st.info("No programmes match the filters.")
        return
    names = {r.programme_id: r.programme_name for r in shown}
    default = profile.get("preferred_programme")
    ids = list(names)
    pid = st.selectbox("Programme", ids, index=ids.index(default) if default in ids else 0, format_func=lambda i: names[i])
    r = next(x for x in shown if x.programme_id == pid)
    e = explain_result(r)
    st.markdown(f"#### {common.DEC_ICON[r.decision]}: {r.programme_name}")
    st.markdown(f"**Logical rule:** `{r.rule_expression}`")
    st.caption(f"Rule version {r.rule_version} | Source: {r.source.get('name')} | Verification: {r.source.get('verification_status')}")
    rows = [{"Condition": c["label"], "Student input": c["student_input"], "Requirement": c["requirement"],
             "Rule": c["logical_rule"], "Result": common.TRI_ICON[c["result"]], "Gap": c["gap"]} for c in e["conditions"]]
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    for c in e["conditions"]:
        with st.expander(f"{common.TRI_ICON[c['result']]}  {c['label']}"):
            st.markdown(f"- **Student input:** {c['student_input']}\n- **Programme requirement:** {c['requirement']}\n"
                        f"- **Logical rule:** `{c['logical_rule']}` → **{c['result']}**\n- **Supporting evidence:** {c['evidence']}\n"
                        f"- **Explanation:** {c['explanation']}\n- **Missing information:** {c['missing_information']}")
    st.markdown(f"**Missing information:** {'; '.join(e['missing_information']) or 'None'}")
    st.markdown(f"**Final decision: {r.decision}.** {r.final_explanation}")
    score, gaps = explanation_completeness(r)
    st.caption(f"Explanation completeness for this decision: {score:.0%}" + (f" (missing: {', '.join(gaps)})" if gaps else ""))
    st.caption(e["notice"])
