import json
import os
from datetime import date

import pandas as pd
import streamlit as st

from database import db
from engine.constants import FIELDS, LEVELS, VERIFICATION_STATUSES, ROOT
from . import common

TEMPLATES = {
    "programmes": {"id": "new_programme", "name": "New programme (illustrative)", "level": "UG", "field": "Computer Science",
                   "description": "", "requirements": [{"id": "overall", "type": "min_overall", "min": 50, "label": "Overall percentage"}],
                   "progression_to": [], "rule_version": 1, "rule_updated": str(date.today()),
                   "source": {"name": "Illustrative sample rule - NOT an official admission criterion", "url": None,
                              "verification_status": "Illustrative sample", "verified_on": None}},
    "certificates": {"id": "new_cert", "name": "New certificate", "issuer": "Issuer", "category": "Academic preparation courses",
                     "fields": [], "skills": [], "knowledge_areas": [], "url": None, "duration": None, "cost": None,
                     "recognition_status": "No institution-specific admission recognition verified",
                     "impact": {"academic_preparation": True, "profile_strengthening": False},
                     "evidence_source": "Describe where this information came from", "verification_status": "Unverified", "verified_on": None},
    "routes": {"id": "new_route", "name": "New route", "route_type": "Bridge route", "alternative_for": ["btech_cse"],
               "final_programme": "btech_cse", "entry_programme": "diploma_cs", "steps": [{"kind": "programme", "programme_id": "diploma_cs"}],
               "why_recommended": "", "steps_to_complete": [], "typical_duration": None, "cost": None, "officially_recognised": "Unverified",
               "recognition_note": "", "source": {"name": "Illustrative sample", "url": None, "verification_status": "Illustrative sample", "verified_on": None}},
}


def _gate() -> bool:
    pw = os.environ.get("APS_ADMIN_PASSWORD")
    if not pw:
        st.caption("Local mode: set the APS_ADMIN_PASSWORD environment variable to require a password here.")
        return True
    if st.session_state.get("admin_ok"):
        return True
    entered = st.text_input("Administrator password", type="password")
    if st.button("Unlock") and entered == pw:
        st.session_state["admin_ok"] = True
        st.rerun()
    return False


def _editor(kind: str, kb: dict, conn):
    items = kb[kind]
    names = {i["id"]: i.get("name", i["id"]) for i in items}
    choice = st.selectbox("Select an item to edit", ["(new from template)"] + list(names), format_func=lambda i: i if i.startswith("(") else f"{names[i]}  [{i}]", key=f"ed_{kind}")
    data = TEMPLATES[kind] if choice.startswith("(") else next(i for i in items if i["id"] == choice)
    text = st.text_area("Item JSON (validated on save)", json.dumps(data, indent=2, ensure_ascii=False), height=380, key=f"ta_{kind}_{choice}")
    note = st.text_input("Change note", key=f"note_{kind}_{choice}")
    c1, c2 = st.columns(2)
    if c1.button("💾 Validate & save", key=f"save_{kind}_{choice}"):
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
            return
        ok, res = db.upsert_kb_item(conn, kind, obj, note)
        if ok:
            st.success(f"Saved. Rule version is now {res}.")
        else:
            for e in res:
                st.error(e)
    if not choice.startswith("(") and c2.button("🗑️ Delete item", key=f"del_{kind}_{choice}"):
        db.delete_kb_item(conn, kind, choice)
        st.rerun()


def render():
    st.title("🛠️ Administrator Dashboard")
    conn = common.get_conn()
    if not _gate():
        return
    kb = common.get_kb()
    st.dataframe(pd.DataFrame([db.admin_stats(conn)]), hide_index=True)
    tabs = st.tabs(["Quick add programme", "Programmes", "Certificates", "Alternative routes", "Sources & verification", "Rule versions", "Export"])
    with tabs[0]:
        st.caption("Simple form for programmes with one overall-percentage rule and up to two subject minimums. Use the Programmes tab for full control.")
        with st.form("quick_prog"):
            a, b = st.columns(2)
            pid = a.text_input("Programme ID (letters, digits, underscore)")
            name = b.text_input("Programme name")
            c, d, e = st.columns(3)
            level = c.selectbox("Level", LEVELS, index=2)
            field = d.selectbox("Field", FIELDS)
            ov = e.number_input("Minimum overall %", 0.0, 100.0, 50.0, 0.5)
            s1, s2 = st.columns(2)
            sub1 = s1.selectbox("Subject minimum 1", ["(none)", "mathematics", "physics", "chemistry", "computer_science"])
            m1 = s1.number_input("Minimum 1", 0.0, 100.0, 50.0, 0.5)
            sub2 = s2.selectbox("Subject minimum 2", ["(none)", "mathematics", "physics", "chemistry", "computer_science"])
            m2 = s2.number_input("Minimum 2", 0.0, 100.0, 50.0, 0.5)
            go = st.form_submit_button("Add programme")
        if go:
            reqs = [{"id": "overall", "type": "min_overall", "min": ov, "label": "Overall percentage (Class 12 / equivalent)"}]
            for sub, m in ((sub1, m1), (sub2, m2)):
                if sub != "(none)" and not any(r["id"] == f"{sub}_min" for r in reqs):
                    reqs.append({"id": f"{sub}_min", "type": "min_subject", "subject": sub, "min": m})
            obj = {**TEMPLATES["programmes"], "id": pid.strip(), "name": name.strip(), "level": level, "field": field, "requirements": reqs}
            ok, res = db.upsert_kb_item(conn, "programmes", obj, "Added via quick form")
            st.success(f"Added (rule version {res}).") if ok else [st.error(e) for e in res]
    with tabs[1]:
        _editor("programmes", kb, conn)
    with tabs[2]:
        _editor("certificates", kb, conn)
    with tabs[3]:
        _editor("routes", kb, conn)
    with tabs[4]:
        st.caption("Mark an item as Verified only with an official URL and a verification date; the validator enforces this.")
        kind = st.selectbox("Item kind", ["programmes", "certificates", "routes"])
        names = {i["id"]: i.get("name", i["id"]) for i in kb[kind]}
        iid = st.selectbox("Item", list(names), format_func=lambda i: names[i])
        item = next(i for i in kb[kind] if i["id"] == iid)
        holder = item if kind == "certificates" else item["source"]
        status = st.selectbox("Verification status", VERIFICATION_STATUSES, index=VERIFICATION_STATUSES.index(holder.get("verification_status", "Unverified")))
        url = st.text_input("Official source URL", holder.get("url") or "")
        vdate = st.text_input("Verified on (YYYY-MM-DD)", holder.get("verified_on") or "")
        srcname = st.text_input("Source name", holder.get("name") if kind != "certificates" else holder.get("evidence_source", ""))
        if st.button("Update source information"):
            holder["verification_status"], holder["url"], holder["verified_on"] = status, url or None, vdate or None
            if kind == "certificates":
                holder["evidence_source"] = srcname
            else:
                holder["name"] = srcname
            ok, res = db.upsert_kb_item(conn, kind, item, "Source / verification update")
            st.success(f"Updated (version {res}).") if ok else [st.error(e) for e in res]
    with tabs[5]:
        st.dataframe(pd.DataFrame(db.kb_history(conn)).head(200), hide_index=True)
    with tabs[6]:
        st.write("Write the current database knowledge base back to the JSON files in `data/` (so edits survive a database reset).")
        if st.button("Export to data/*.json"):
            st.success("Written: " + ", ".join(os.path.relpath(p, ROOT) for p in db.export_kb_to_json(conn)))
