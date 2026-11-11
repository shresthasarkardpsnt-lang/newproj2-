import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from engine.kb import prog_by_id
from engine.pathway import NO_GUARANTEE, build_route_graph, draw_graph, find_routes
from . import common

ICON = {"Eligible": "✅", "Needs review": "❓", "Not eligible": "❌"}


def render():
    st.title("🧭 Alternative Academic Pathways")
    kb = common.get_kb()
    profile = common.require_profile()
    common.sample_notice(kb)
    st.warning(NO_GUARANTEE)
    pid = common.pick_programme(kb, profile, "Target programme you would like to reach", "routes_target")
    target = prog_by_id(kb, pid)
    from engine.eligibility import evaluate_programme
    from engine.kb import cert_names
    direct = evaluate_programme(profile, target, cert_names(kb))
    st.markdown(f"**Direct eligibility for {target['name']}:** {common.DEC_ICON[direct.decision]}")
    if direct.decision == "Eligible":
        st.success("You are already eligible for this programme under the sample rule. Alternatives are shown for information only.")

    routes = find_routes(profile, pid, kb)
    if not routes:
        st.info("No alternative routes are stored for this programme. An administrator can add some.")
        return
    st.write(f"{len(routes)} route(s) found, ordered by how many entry requirements you currently meet.")
    for e in routes:
        with st.expander(f"{ICON.get(e['entry_decision'], '•')} {e['name']}  -  {e['entry_decision']}"):
            st.markdown(f"**Route type:** {e['route_type']}  |  **Leads to:** {e['final_programme']}")
            st.markdown(f"**Why it is recommended:** {e['why']}")
            st.markdown(f"**Your current position:** {e['why_now']}")
            fig = draw_graph(build_route_graph(e, target["name"]))
            st.pyplot(fig)
            plt.close(fig)
            st.markdown("**Steps**")
            for s in e["steps"]:
                st.markdown(f"{s['index']}. **{s['label']}**  -  _{s['status']}_")
                if s["requirements"]:
                    st.caption("Requirements: " + " AND ".join(s["requirements"]))
                if s.get("note"):
                    st.caption(s["note"])
            if e["missing"]:
                st.markdown("**Missing requirements for the first step**")
                st.dataframe(pd.DataFrame([{"Condition": c.label, "Student": c.student_value, "Required": c.required,
                                            "Result": common.TRI_ICON[c.result.value], "Gap": c.gap_text} for c in e["missing"]]), hide_index=True)
            elif e["entry"] is not None:
                st.success("No missing requirements for the first step.")
            st.markdown("**Steps to complete**")
            for i, t in enumerate(e["steps_to_complete"], 1):
                st.markdown(f"{i}. {t}")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Duration:** {e['duration']}")
            c2.markdown(f"**Cost:** {e['cost']}")
            c3.markdown(f"**Officially recognised:** {e['officially_recognised']}")
            st.caption(e["recognition_note"])
            src = e["source"]
            st.caption(f"Source: {src.get('name')} | Verification status: {src.get('verification_status')} | "
                       f"Verified on: {src.get('verified_on') or 'not verified'} | URL: {src.get('url') or 'none'}")
            st.caption(e["disclaimer"])
