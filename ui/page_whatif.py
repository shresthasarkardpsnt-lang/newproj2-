import pandas as pd
import streamlit as st

from engine.constants import CORE_SUBJECTS, ENTRANCE_STATUSES, STREAMS, SUBJECT_LABELS
from engine.kb import all_exams
from engine.simulator import simulate
from . import common

KEEP = "(keep actual)"


def _slider(label, actual, key):
    use = st.checkbox(f"Change {label}", key=key + "_use")
    val = st.slider(label, 0.0, 100.0, float(actual) if actual is not None else 50.0, 0.5, key=key + "_val", disabled=not use)
    st.caption(f"Actual: {'not provided' if actual is None else f'{actual:g}%'}")
    return val if use else None


def render():
    st.title("🎛️ What-if Academic Simulator")
    kb = common.get_kb()
    profile = common.require_profile()
    st.error("HYPOTHETICAL MODE: values below are simulated. Your saved profile and marks are never changed.")
    left, right = st.columns([1, 2])
    with left:
        st.subheader("Hypothetical values")
        overall = _slider("Overall percentage", profile.get("overall_pct"), "wi_ov")
        maths = _slider("Mathematics marks", profile["marks"].get("mathematics"), "wi_ma")
        phys = _slider("Physics marks", profile["marks"].get("physics"), "wi_ph")
        other_subj = st.selectbox("Another subject", ["(none)"] + [s for s in CORE_SUBJECTS if s not in ("mathematics", "physics")],
                                  format_func=lambda s: s if s == "(none)" else SUBJECT_LABELS[s])
        other = _slider("Other subject marks", profile["marks"].get(other_subj) if other_subj != "(none)" else None, f"wi_ot_{other_subj}") if other_subj != "(none)" else None
        stream = st.selectbox("Academic stream", [KEEP] + STREAMS)
        ex = st.selectbox("Entrance exam", ["(none)"] + all_exams(kb))
        ex_status = st.selectbox("Hypothetical entrance status", ENTRANCE_STATUSES[1:], index=len(ENTRANCE_STATUSES) - 2) if ex != "(none)" else None
    overrides = {"overall_pct": overall, "marks": {"mathematics": maths, "physics": phys},
                 "stream": None if stream == KEEP else stream}
    if other is not None:
        overrides["marks"][other_subj] = other
    if ex_status:
        overrides["entrance_exams"] = {ex: {"status": ex_status, "score": None}}
    sim = simulate(profile, overrides, kb)
    with right:
        st.subheader("Result (HYPOTHETICAL)")
        a, b = st.columns(2)
        cur_e = sum(1 for r in sim["current"] if r.decision == "Eligible")
        hyp_e = sum(1 for r in sim["hypothetical"] if r.decision == "Eligible")
        a.metric("Currently eligible programmes", cur_e)
        b.metric("Hypothetically eligible programmes", hyp_e, delta=hyp_e - cur_e)
        if sim["newly_eligible"]:
            st.success("Newly eligible (hypothetical): " + "; ".join(sim["newly_eligible"]))
        if sim["no_longer_eligible"]:
            st.warning("No longer eligible (hypothetical): " + "; ".join(sim["no_longer_eligible"]))
        if not sim["newly_eligible"] and not sim["no_longer_eligible"]:
            st.info("No programme changes eligibility with these values.")
        df = pd.DataFrame(sim["rows"])
        for c in ("Current", "Hypothetical"):
            df[c] = df[c].map(common.DEC_ICON)
        st.dataframe(df, hide_index=True)
        st.markdown("**Conditions changing (hypothetical)**")
        if sim["transitions"]:
            st.dataframe(pd.DataFrame(sim["transitions"]), hide_index=True)
        else:
            st.write("None.")
        st.markdown("**Failed conditions that would remain**")
        if sim["remaining_failed"]:
            for prog, items in sim["remaining_failed"].items():
                st.markdown(f"- **{prog}**: " + "; ".join(f"{l} ({g})" for l, g in items))
        else:
            st.write("None - no condition would remain FALSE.")
        st.caption("✅ Verified: your actual profile was not modified." if sim["profile_unchanged"] else "⚠️ Profile changed unexpectedly!")
        st.caption("Simulated marks do not represent real results and are not saved.")
