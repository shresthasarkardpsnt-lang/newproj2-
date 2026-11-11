"""Simplified profile page: only the essentials, optional details tucked away."""
import streamlit as st

from database import db
from engine.constants import BASE_ENTRANCE_EXAMS, DISCIPLINES, ENTRANCE_NOT_SPECIFIED, ENTRANCE_STATUSES, STREAMS
from engine.kb import all_exams
from engine.logic import to_number
from engine.validation import default_profile, normalise_profile, validate_profile
from . import common

NS = "Not specified"
YN = {NS: None, "Yes": True, "No": False}


def _t(v):
    return "" if v is None else f"{v:g}"


def render():
    st.title("🧑‍🎓 My Profile")
    st.caption("Fill in what you know. Anything left blank is treated as unknown, never guessed.")
    kb, conn = common.get_kb(), common.get_conn()
    existing = common.current_profile()
    p = normalise_profile(existing or default_profile())
    is_new = existing is None
    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash[0])
    if is_new and st.button("Try a demo student"):
        common.select_student(db.save_student(conn, common.demo_profile()))
        st.rerun()
    k = f"lp_{p['student_id'] or 'new'}_"
    with st.form(k + "form"):
        a, b = st.columns(2)
        sid = a.text_input("Student ID or name *", p["student_id"], disabled=not is_new, key=k + "sid")
        stream = b.selectbox("Stream", [NS] + STREAMS, index=([NS] + STREAMS).index(p["stream"]) if p["stream"] in STREAMS else 0, key=k + "stream")
        a, b, c, d = st.columns(4)
        overall = a.text_input("Overall % (Class 12)", _t(p["overall_pct"]), key=k + "ov")
        maths = b.text_input("Mathematics %", _t(p["marks"]["mathematics"]), key=k + "ma")
        phys = c.text_input("Physics %", _t(p["marks"]["physics"]), key=k + "ph")
        chem = d.text_input("Chemistry %", _t(p["marks"]["chemistry"]), key=k + "ch")
        labels = common.programme_labels(kb)
        opts = [None] + list(labels)
        pref = st.selectbox("Programme you want", opts, index=opts.index(p["preferred_programme"]) if p["preferred_programme"] in labels else 0,
                            format_func=lambda i: "(not chosen)" if i is None else labels[i], key=k + "pref")
        with st.expander("More details (optional)"):
            a, b, c = st.columns(3)
            c10 = a.text_input("Class 10 %", _t(p["class10_pct"]), key=k + "c10")
            cs = b.text_input("Computer Science %", _t(p["marks"]["computer_science"]), key=k + "cs")
            eng = c.text_input("English %", _t(p["marks"]["english"]), key=k + "en")
            st.markdown("**Entrance exams**")
            ent, cols = {}, st.columns(3)
            for i, ex in enumerate(dict.fromkeys(BASE_ENTRANCE_EXAMS + all_exams(kb))):
                cur = (p["entrance_exams"].get(ex) or {}).get("status") or ENTRANCE_NOT_SPECIFIED
                ent[ex] = cols[i % 3].selectbox(ex, ENTRANCE_STATUSES, index=ENTRANCE_STATUSES.index(cur) if cur in ENTRANCE_STATUSES else 0, key=f"{k}e_{ex}")
            st.markdown("**Diploma / bachelor's degree**")
            a, b, c, d = st.columns(4)
            dh = a.selectbox("Diploma?", list(YN), index=list(YN).index({None: NS, True: "Yes", False: "No"}[p["diploma"]["has"]]), key=k + "dh")
            dp = b.text_input("Diploma %", _t(p["diploma"]["pct"]), key=k + "dp")
            bh = c.selectbox("Bachelor's?", list(YN), index=list(YN).index({None: NS, True: "Yes", False: "No"}[p["bachelor"]["has"]]), key=k + "bh")
            bp = d.text_input("Bachelor's %", _t(p["bachelor"]["pct"]), key=k + "bp")
            bd = st.selectbox("Bachelor's discipline", [NS] + DISCIPLINES, index=([NS] + DISCIPLINES).index(p["bachelor"]["discipline"]) if p["bachelor"]["discipline"] in DISCIPLINES else 0, key=k + "bd")
        go = st.form_submit_button("💾 Save and see results", type="primary")
    if not go:
        return
    raw = normalise_profile(p)
    raw.update({"student_id": sid.strip(), "stream": None if stream == NS else stream, "overall_pct": overall,
                "class10_pct": c10, "preferred_programme": pref})
    raw["marks"].update({"mathematics": maths, "physics": phys, "chemistry": chem, "computer_science": cs, "english": eng})
    for s, v in raw["marks"].items():
        if str(v).strip() != "" and raw["studied"].get(s) is False:
            raw["studied"][s] = None
    raw["entrance_exams"] = {e: {"status": None if v == ENTRANCE_NOT_SPECIFIED else v, "score": (p["entrance_exams"].get(e) or {}).get("score")} for e, v in ent.items()}
    raw["diploma"].update({"has": YN[dh], "pct": dp})
    raw["bachelor"].update({"has": YN[bh], "pct": bp, "discipline": None if bd == NS else bd})
    errors, _ = validate_profile(raw)
    if is_new and sid.strip() and db.get_student(conn, sid.strip()):
        errors.append(f"'{sid.strip()}' already exists. Choose another ID or select that student in the sidebar.")
    if errors:
        for e in errors:
            st.error(e)
        return
    clean = normalise_profile(raw)
    for key in ("class10_pct", "overall_pct"):
        clean[key] = to_number(raw[key])
    clean["marks"] = {s: to_number(v) for s, v in raw["marks"].items()}
    clean["diploma"]["pct"], clean["bachelor"]["pct"] = to_number(raw["diploma"]["pct"]), to_number(raw["bachelor"]["pct"])
    saved = db.save_student(conn, clean)
    st.session_state["flash"] = (f"Saved '{saved}'. Taking you to your programmes.", [])
    common.select_student(saved)
    st.rerun()
