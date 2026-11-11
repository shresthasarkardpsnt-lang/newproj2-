import streamlit as st

from database import db
from engine.constants import (BASE_ENTRANCE_EXAMS, CAREER_INTERESTS, CORE_SUBJECTS, DIPLOMA_BRANCHES, DISCIPLINES,
                              ENTRANCE_NOT_SPECIFIED, ENTRANCE_STATUSES, STREAMS, SUBJECT_LABELS)
from engine.kb import all_exams
from engine.logic import to_number
from engine.validation import default_profile, normalise_profile, validate_profile
from . import common

NS = "Not specified"
YN = [NS, "Yes", "No"]
TO_TRI = {NS: None, "Yes": True, "No": False}
FROM_TRI = {None: NS, True: "Yes", False: "No"}


def _txt(v):
    return "" if v is None else f"{v:g}" if isinstance(v, (int, float)) else str(v)


def _sel(options, value, none_label=NS):
    return options.index(value) if value in options else 0


def render():
    st.title("🧑‍🎓 Student Profile")
    st.caption("Leave a field blank or 'Not specified' if you don't know it. Missing information is treated as UNKNOWN, never guessed.")
    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash[0])
        for w in flash[1]:
            st.warning(w)
    kb, conn = common.get_kb(), common.get_conn()
    existing = common.current_profile()
    p = normalise_profile(existing or default_profile())
    is_new = existing is None
    if is_new:
        c1, c2 = st.columns([3, 1])
        c1.info("Creating a new profile.")
        if c2.button("Load demo student"):
            common.select_student(db.save_student(conn, common.demo_profile()))
            st.rerun()
    k = f"pf_{p['student_id'] or 'new'}_"
    with st.form(k + "form"):
        st.subheader("Identity")
        a, b = st.columns(2)
        sid = a.text_input("Student ID (or name)*", value=p["student_id"], disabled=not is_new, key=k + "sid",
                           help="Used as the unique record key; cannot be changed after creation.")
        name = b.text_input("Full name (optional)", value=p["name"], key=k + "name")

        st.subheader("Academic record")
        a, b, c, d = st.columns(4)
        c10 = a.text_input("Class 10 %", _txt(p["class10_pct"]), key=k + "c10")
        c12 = b.text_input("Class 12 %", _txt(p["class12_pct"]), key=k + "c12")
        stream = c.selectbox("Academic stream", [NS] + STREAMS, index=_sel([NS] + STREAMS, p["stream"]), key=k + "stream")
        overall = d.text_input("Overall % (Class 12 / equivalent)", _txt(p["overall_pct"]), key=k + "overall")

        st.markdown("**Subject marks and whether the subject was studied**")
        marks, studied = {}, {}
        for s in CORE_SUBJECTS:
            m, f = st.columns([2, 1])
            marks[s] = m.text_input(f"{SUBJECT_LABELS[s]} marks (%)", _txt(p["marks"].get(s)), key=f"{k}m_{s}")
            studied[s] = f.selectbox(f"{SUBJECT_LABELS[s]} studied?", YN, index=YN.index(FROM_TRI[p["studied"].get(s)]), key=f"{k}s_{s}")
        others_txt = st.text_area("Other subject marks (one per line, e.g. `Statistics = 72`)",
                                  "\n".join(f"{n} = {_txt(v)}" for n, v in p["other_subjects"].items()), key=k + "others")

        with st.expander("Entrance examinations", expanded=True):
            exams = list(dict.fromkeys(BASE_ENTRANCE_EXAMS + all_exams(kb)))
            ent = {}
            for ex in exams:
                cur = p["entrance_exams"].get(ex) or {}
                a, b = st.columns([2, 1])
                status = a.selectbox(f"{ex} status", ENTRANCE_STATUSES,
                                     index=_sel(ENTRANCE_STATUSES, cur.get("status") or ENTRANCE_NOT_SPECIFIED, ENTRANCE_NOT_SPECIFIED), key=f"{k}e_{ex}")
                score = b.text_input(f"{ex} score", _txt(cur.get("score")), key=f"{k}es_{ex}")
                ent[ex] = {"status": None if status == ENTRANCE_NOT_SPECIFIED else status, "score": score}

        with st.expander("Diploma / bachelor's degree"):
            a, b, c = st.columns(3)
            d_has = a.selectbox("Holds a diploma?", YN, index=YN.index(FROM_TRI[p["diploma"]["has"]]), key=k + "dh")
            d_branch = b.selectbox("Diploma branch", [NS] + DIPLOMA_BRANCHES, index=_sel([NS] + DIPLOMA_BRANCHES, p["diploma"]["branch"]), key=k + "db")
            d_pct = c.text_input("Diploma %", _txt(p["diploma"]["pct"]), key=k + "dp")
            a, b, c, d = st.columns(4)
            b_has = a.selectbox("Holds a bachelor's degree?", YN, index=YN.index(FROM_TRI[p["bachelor"]["has"]]), key=k + "bh")
            b_deg = b.text_input("Degree name", p["bachelor"].get("degree", ""), key=k + "bd")
            b_disc = c.selectbox("Discipline", [NS] + DISCIPLINES, index=_sel([NS] + DISCIPLINES, p["bachelor"]["discipline"]), key=k + "bdi")
            b_pct = d.text_input("Bachelor's %", _txt(p["bachelor"]["pct"]), key=k + "bp")

        st.subheader("Additional qualifications & certificates")
        addl = st.text_area("Other qualifications (free text, one per line; informational only)",
                            "\n".join(p["additional_qualifications"]), key=k + "addl",
                            help="Free text is NOT used for eligibility. Only certificates named in a programme rule can matter.")
        cert_labels = {c["id"]: c["name"] for c in kb["certificates"]}
        certs = st.multiselect("Completed certificates (from the knowledge base)", list(cert_labels), default=[c for c in p["certificates"] if c in cert_labels],
                               format_func=lambda i: cert_labels[i], key=k + "certs")

        st.subheader("Goals")
        labels = common.programme_labels(kb)
        pref = st.selectbox("Preferred programme", [None] + list(labels), index=([None] + list(labels)).index(p["preferred_programme"]) if p["preferred_programme"] in labels else 0,
                            format_func=lambda i: "(not chosen)" if i is None else labels[i], key=k + "pref")
        interests = st.multiselect("Career interests", CAREER_INTERESTS, default=[i for i in p["career_interests"] if i in CAREER_INTERESTS], key=k + "int")
        submitted = st.form_submit_button("💾 Save profile", type="primary")

    if submitted:
        others, other_errors = {}, []
        for line in [l for l in others_txt.splitlines() if l.strip()]:
            if "=" not in line and ":" not in line:
                other_errors.append(f"Cannot read other-subject line: '{line}'. Use 'Subject = mark'.")
                continue
            nm, _, val = line.replace(":", "=", 1).partition("=")
            others[nm.strip()] = val.strip()
        raw = {"student_id": sid.strip(), "name": name.strip(), "class10_pct": c10, "class12_pct": c12,
               "stream": None if stream == NS else stream, "overall_pct": overall,
               "marks": marks, "other_subjects": others, "studied": {s: TO_TRI[v] for s, v in studied.items()},
               "entrance_exams": ent,
               "diploma": {"has": TO_TRI[d_has], "branch": None if d_branch == NS else d_branch, "pct": d_pct},
               "bachelor": {"has": TO_TRI[b_has], "degree": b_deg, "discipline": None if b_disc == NS else b_disc, "pct": b_pct},
               "additional_qualifications": [l.strip() for l in addl.splitlines() if l.strip()],
               "certificates": certs, "preferred_programme": pref, "career_interests": interests}
        errors, warnings = validate_profile(raw)
        errors = other_errors + errors
        if is_new and sid.strip() and db.get_student(conn, sid.strip()):
            errors.append(f"A student with ID '{sid.strip()}' already exists. Pick another ID or load that student.")
        if errors:
            for e in errors:
                st.error(e)
            st.stop()
        clean = normalise_profile(raw)
        for key in ("class10_pct", "class12_pct", "overall_pct"):
            clean[key] = to_number(raw[key])
        clean["marks"] = {s: to_number(v) for s, v in marks.items()}
        clean["other_subjects"] = {n: to_number(v) for n, v in others.items()}
        for ex in clean["entrance_exams"].values():
            ex["score"] = to_number(ex["score"], 0, 1e9)
        for key in ("diploma", "bachelor"):
            clean[key]["pct"] = to_number(raw[key]["pct"])
        saved = db.save_student(conn, clean)
        db.sync_certificates(conn, saved, certs)
        common.select_student(saved)
        st.session_state["flash"] = (f"Profile '{saved}' saved.", warnings)
        st.rerun()

    if existing is not None:
        st.divider()
        with st.expander("Danger zone"):
            if st.checkbox(f"I understand this permanently deletes '{existing['student_id']}' and all its history", key=k + "delconf"):
                if st.button("Delete this student", key=k + "del"):
                    db.delete_student(conn, existing["student_id"])
                    common.select_student(None)
                    st.rerun()
