"""Main evaluation: one simple table, then a plain explanation for one programme."""
import pandas as pd
import streamlit as st

from engine.eligibility import evaluate_all
from engine.logic import Tri
from engine.reports import evaluation_pdf
from . import common


def short_reason(r) -> str:
    if r.decision == "Eligible":
        return "You meet every requirement."
    parts = [f"{c.label.split(' (')[0]}: {c.gap_text.replace(' percentage points', ' pts short')}" for c in r.failed]
    if r.decision == "Needs review":
        parts = ["Need: " + "; ".join(m.split(' for: ')[0] for m in r.missing_information)]
    elif r.unknown:
        parts.append(f"+{len(r.unknown)} unknown")
    return "; ".join(parts)


def render():
    st.title("📋 Eligibility Results")
    kb = common.get_kb()
    profile = common.require_profile()
    results = evaluate_all(profile, kb)
    n = lambda d: sum(1 for r in results if r.decision == d)
    a, b, c = st.columns(3)
    a.metric("✅ Eligible", n("Eligible"))
    b.metric("❌ Not eligible", n("Not eligible"))
    c.metric("❓ Needs review", n("Needs review"))
    show = st.radio("Show", ["All", "Eligible", "Not eligible", "Needs review"], horizontal=True)
    rows = [r for r in results if show in ("All", r.decision)]
    st.dataframe(pd.DataFrame([{"Programme": r.programme_name, "Result": common.DEC_ICON[r.decision], "Why": short_reason(r)} for r in rows]),
                 hide_index=True)

    if not rows:
        return
    st.subheader("Why this result?")
    ids = {r.programme_id: r.programme_name for r in rows}
    keys = list(ids)
    pref = profile.get("preferred_programme")
    pid = st.selectbox("Pick a programme", keys, index=keys.index(pref) if pref in keys else 0, format_func=lambda i: ids[i])
    r = next(x for x in rows if x.programme_id == pid)
    st.dataframe(pd.DataFrame([{"Requirement": c.label, "You": c.student_value, "Needed": c.required, "Result": common.TRI_ICON[c.result.value]}
                               for c in r.conditions]), hide_index=True)
    st.markdown(f"**{common.DEC_ICON[r.decision]}.** {r.final_explanation}")
    st.caption(f"Rule used: `{r.rule_expression}`")
    st.download_button("⬇️ Download PDF report", evaluation_pdf(profile, rows), "eligibility_report.pdf", "application/pdf")
    st.caption("Sample criteria are illustrative, not official. Confirm with the institution.")
