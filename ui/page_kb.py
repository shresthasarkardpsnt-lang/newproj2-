import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from engine.constants import LEVELS, VERIFICATION_STATUSES
from engine.eligibility import evaluate_programme
from engine.pathway import draw_progression, progression_graph
from engine.validation import default_profile
from . import common


def _src(p):
    s = p.get("source", {})
    return s.get("verification_status", "Unverified")


def render():
    st.title("📖 Programme Knowledge Base")
    kb = common.get_kb()
    common.sample_notice(kb)
    t1, t2, t3, t4 = st.tabs(["Programmes", "Certificates", "Alternative routes", "Progression graph"])
    with t1:
        c1, c2, c3 = st.columns(3)
        lv = c1.multiselect("Level", LEVELS, default=LEVELS)
        fl = c2.multiselect("Field", sorted({p["field"] for p in kb["programmes"]}), default=sorted({p["field"] for p in kb["programmes"]}))
        vs = c3.multiselect("Verification", VERIFICATION_STATUSES, default=VERIFICATION_STATUSES)
        rows = [p for p in kb["programmes"] if p["level"] in lv and p["field"] in fl and _src(p) in vs]
        st.dataframe(pd.DataFrame([{"Programme": p["name"], "Level": p["level"], "Field": p["field"],
                                    "Rules": len(p["requirements"]), "Rule version": p.get("rule_version", 1),
                                    "Verification": _src(p), "Verified on": p["source"].get("verified_on") or "-"} for p in rows]), hide_index=True)
        if rows:
            names = {p["id"]: p["name"] for p in rows}
            pid = st.selectbox("Show requirements", list(names), format_func=lambda i: names[i])
            p = next(x for x in rows if x["id"] == pid)
            res = evaluate_programme(default_profile(), p)
            st.markdown(f"**Logical rule:** `Eligible = {res.rule_expression}`")
            st.dataframe(pd.DataFrame([{"Requirement": c.label, "Rule": c.rule, "Required": c.required} for c in res.conditions]), hide_index=True)
            st.caption(f"Source: {p['source'].get('name')} | URL: {p['source'].get('url') or 'none'} | Status: {_src(p)} | "
                       f"Rule version {p.get('rule_version', 1)} (updated {p.get('rule_updated', '-')})")
            ups = [x["name"] for x in kb["programmes"] if p["id"] in x.get("progression_to", [])]
            st.write("Progresses from: " + (", ".join(ups) or "-") + "   |   Progresses to: " +
                     (", ".join(next((x["name"] for x in kb["programmes"] if x["id"] == t), t) for t in p.get("progression_to", [])) or "-"))
    with t2:
        st.dataframe(pd.DataFrame([{"Certificate": c["name"], "Issuer": c["issuer"], "Category": c["category"],
                                    "URL": c["url"] or "-", "Duration": c["duration"] or "Not verified", "Cost": c["cost"] or "Not verified",
                                    "Recognition": c["recognition_status"], "Verification": c["verification_status"]} for c in kb["certificates"]]), hide_index=True)
    with t3:
        names = {p["id"]: p["name"] for p in kb["programmes"]}
        st.dataframe(pd.DataFrame([{"Route": r["name"], "Type": r.get("route_type", ""),
                                    "Alternative for": ", ".join(names.get(t, t) for t in r["alternative_for"]),
                                    "Leads to": names.get(r["final_programme"], r["final_programme"]),
                                    "Recognised": r.get("officially_recognised"), "Verification": r["source"].get("verification_status")} for r in kb["routes"]]), hide_index=True)
    with t4:
        st.caption("Illustrative progression relationships between programmes (arrows: can lead to).")
        fig = draw_progression(progression_graph(kb))
        st.pyplot(fig)
        plt.close(fig)
