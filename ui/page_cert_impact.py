import pandas as pd
import streamlit as st

from engine.certificates import cert_flags, certificate_impact
from engine.constants import CERT_CATEGORIES
from . import common


def render():
    st.title("🧪 Certificate Impact Analysis")
    kb = common.get_kb()
    common.sample_notice(kb)
    st.markdown("""
| Effect | Meaning |
|---|---|
| **Formal admission eligibility** | Only when a programme rule in the knowledge base explicitly names the certificate |
| **Academic preparation** | Builds knowledge in an area; does not change recorded marks |
| **Skills / profile** | Shows additional skills; no formal admission effect |
| **Recognition unverified** | No verified evidence that an institution accepts it for admission |
""")
    cat = st.selectbox("Category", ["All"] + CERT_CATEGORIES)
    rows = []
    for c in kb["certificates"]:
        if cat != "All" and c["category"] != cat:
            continue
        f = cert_flags(c, kb)
        rows.append({"Certificate": c["name"], "Issuer": c["issuer"], "Category": c["category"],
                     "Formal eligibility": "✅ " + ", ".join(f["formal_programmes"]) if f["improves_formal_eligibility"] else "❌ None",
                     "Academic preparation": "✅" if f["improves_academic_preparation"] else "➖",
                     "Skills/profile": "✅" if f["strengthens_profile"] else "➖",
                     "Recognition unverified": "⚠️ Yes" if f["admission_recognition_unverified"] else "No",
                     "Verification": c["verification_status"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True)

    st.subheader("Effect on your eligibility if you completed a certificate")
    profile = common.current_profile()
    if profile is None:
        st.info("Select a student to see the effect on a real profile.")
        return
    names = {c["id"]: c["name"] for c in kb["certificates"]}
    cid = st.selectbox("Certificate", list(names), format_func=lambda i: names[i])
    imp = certificate_impact(profile, cid, kb)
    st.write("Marks, percentages and stream are unchanged by completing a certificate." if imp["marks_unchanged"] else "⚠️ Unexpected change in marks!")
    if imp["changes"]:
        st.success("Eligibility changes only where a rule explicitly names this certificate:")
        for ch in imp["changes"]:
            st.markdown(f"- **{ch['programme']}**: {ch['before']} → {ch['after']}; conditions: "
                        + ", ".join(f"{l}: {a} → {b}" for l, a, b in ch["conditions_changed"]))
        st.caption("This reflects an illustrative sample rule. Confirm acceptance with the real institution.")
    else:
        st.info("No programme's eligibility changes. No rule in the knowledge base names this certificate, so it has no formal admission effect.")
