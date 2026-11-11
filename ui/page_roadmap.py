import streamlit as st

from database import db
from engine.eligibility import evaluate_all
from engine.reports import roadmap_pdf
from engine.roadmap import build_roadmap
from . import common


def render():
    st.title("🗺️ Academic Improvement Roadmap")
    kb, conn = common.get_kb(), common.get_conn()
    profile = common.require_profile()
    common.sample_notice(kb)
    pid = common.pick_programme(kb, profile, "Target programme", "rm_target")
    sid = profile["student_id"]
    rm = build_roadmap(profile, kb, pid, db.get_progress(conn, sid, pid))
    st.info(rm["note"])
    st.progress(rm["progress"], text=f"Progress: {rm['done']} of {rm['total']} items checked  |  Current decision: {rm['decision']}")
    for s in rm["stages"]:
        st.subheader(f"{s['stage']}. {s['title']}")
        if s["stage"] == 6:
            comp = s["completed_certificates"]
            names = {c["id"]: c["name"] for c in kb["certificates"]}
            st.write("Completed: " + (", ".join(names.get(c, c) for c in comp) if comp else "none yet. Tick certificates in stages 3 and 4."))
            continue
        if s["stage"] == 7:
            st.write(f"**Current decision: {common.DEC_ICON[s['decision']]}.** {s['explanation']}")
            if st.button("🔄 Re-evaluate eligibility now and save to history"):
                results = evaluate_all(profile, kb)
                run = db.save_evaluation(conn, sid, profile, results, note="Roadmap re-evaluation")
                st.success(f"Re-evaluated and saved as run #{run}. Marks were not changed by roadmap progress.")
            continue
        if not s["items"]:
            st.write(s["empty"])
        for it in s["items"]:
            label = it["text"] + ("" if it.get("verified", True) else "  ⚠️ unverified")
            val = st.checkbox(label, value=it["done"], key=f"rm_{pid}_{it['key']}", help=it["detail"])
            if it["detail"]:
                st.caption(it["detail"])
            if val != it["done"]:
                if "cert_id" in it:
                    db.set_certificate_completed(conn, sid, it["cert_id"], val)
                else:
                    db.set_progress(conn, sid, pid, it["key"], val)
                st.rerun()
    st.download_button("⬇️ Roadmap PDF", roadmap_pdf(profile, rm), "roadmap.pdf", "application/pdf")
