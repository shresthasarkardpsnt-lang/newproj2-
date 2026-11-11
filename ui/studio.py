"""Applicant interface (redesigned): five short pages, plain-HTML visuals, nothing hidden behind interactive tables.

Maps one-to-one onto the brief:
  Eligible programmes ........ page 2   Missing conditions ........ page 3
  Alternative pathways ....... page 3   Reasoning chain ........... pages 2 + 4
  Confidence / evidence ...... pages 2 + 4   Exception handling ..... pages 2 + 4
  Human-review states ........ pages 2 + 4   Baseline + metrics .... pages 4 + 5
"""
from __future__ import annotations

import streamlit as st

from engine import applicant as A
from engine.constants import LEVELS
from engine.evaluation import run_suite
from engine.reports import evaluation_pdf
from engine.simulator import simulate
from . import common, lite_profile, theme
from .theme import Raw, esc

PAGES = ["1 · Profile", "2 · Programmes", "3 · Gaps & pathways", "4 · Reasoning", "5 · Quality & KB"]
ALL = ["All"]


# ------------------------------------------------------------------ shared bits
def need_profile() -> dict:
    p = common.current_profile()
    if p is None:
        theme.note("No student selected yet. Pick one in the sidebar, or fill in the Profile page (step 1). "
                   "You can also load the sample student there.")
        st.stop()
    return p


def card_html(c: dict) -> str:
    kind, label = theme.DECISION[c["decision"]]
    conf, rv = c["confidence"], c["review"]
    pct = 100 * c["passed"] / max(c["total"], 1)
    return (f"<div class='aps-card {kind}'>{theme.ring(pct, kind)}<div class='aps-body'><h4>{esc(c['name'])}</h4><div class='aps-sub'>{esc(c['level'])} · {esc(c['field'])}</div>"
            f"{theme.pill(label, kind)}{theme.pill('Confidence: ' + conf['label'], theme.CONF[conf['label']])}"
            f"{theme.pill_raw(rv['label'], theme.REVIEW[rv['code']])}"
            f"<div style='margin-top:6px'>{esc(c['headline'])}</div>{theme.meter(c['passed'], c['failed'], c['unknown'])}"
            f"<div class='aps-sub'>{c['passed']} met · {c['unknown']} unknown · {c['failed']} not met (of {c['total']} conditions)</div></div></div>")


def chain_html(steps: list) -> str:
    out = []
    for s in steps:
        kind, lab = theme.TRI[s["result"]]
        kids = "".join(f"<small>↳ {esc(k['label'])}: {esc(k['student_input'])} → {esc(theme.TRI[k['result']][1])}</small>" for k in s["children"])
        out.append(f"<div class='aps-step'><div class='aps-num'>{s['n']}</div><div><b>{esc(s['label'])}</b> {theme.pill(lab, kind)}"
                   f"<small>You: {esc(s['student_input'])} · Needed: {esc(s['requirement'])}</small>"
                   f"<small>Rule: <code>{esc(s['logical_rule'])}</code></small>"
                   f"<small>Evidence: {esc(s['evidence'])}</small><small>{esc(s['explanation'])}</small>{kids}</div></div>")
    return "".join(out)


def conclusion_block(c: dict) -> None:
    conf, rv = c["confidence"], c["review"]
    theme.show(f"<div class='aps-note info'>"
               f"<b>Conclusion:</b> {esc(A.conclusion_sentence(c['result']))}<br>"
               f"<b>Confidence {esc(conf['label'])}</b> ({conf['pct']:.0%} of conditions checked): {esc(conf['basis'])}<br>"
               f"<b>{esc(rv['label'])}:</b> {esc(rv['why'])}</div>")


def exceptions_block(c: dict) -> None:
    theme.table(["Exception", "How it was handled"], [(k, m) for k, m in c["exceptions"]])


def pick(cards: list, key: str, label: str, profile: dict, prefer_open: bool = True) -> dict:
    by = {c["id"]: c for c in cards}
    pref = profile.get("preferred_programme")
    default = pref if pref in by else next((c["id"] for c in cards if prefer_open and c["decision"] != "Eligible"), cards[0]["id"])
    ids = list(by)
    if st.session_state.get(key) not in by:
        st.session_state[key] = default
    pid = st.selectbox(label, ids, key=key, format_func=lambda i: f"{by[i]['name']}  ·  {by[i]['decision']}")
    return by[pid]


# ------------------------------------------------------------------ 1 profile
def page_profile() -> None:
    theme.hero("Tell us about yourself", "Fill in what you know. Anything left blank is treated as unknown, never guessed.")
    lite_profile.render()


# ------------------------------------------------------------------ 2 programmes
def page_programmes() -> None:
    profile, kb = need_profile(), common.get_kb()
    cards = A.programme_cards(profile, kb)
    sid = profile["student_id"]
    n = lambda d: sum(1 for c in cards if c["decision"] == d)
    queue = [c for c in cards if c["review"]["code"] != "auto" and not st.session_state.get(f"rv_{sid}_{c['id']}")]
    theme.hero("Your programmes", f"{profile.get('name') or sid}: every programme checked against its rules, with the reasoning behind each answer.")
    theme.stats([(n("Eligible"), "Eligible", "aps-ok"), (n("Needs review"), "Needs review", "aps-rv"),
                 (n("Not eligible"), "Not eligible", "aps-no"), (len(queue), "Awaiting human review", "aps-in")])
    a, b, c3 = st.columns([2, 3, 2])
    q = a.text_input("Search", key="pg_q", placeholder="e.g. data, B.Tech, MCA").strip().lower()
    show_ = b.radio("Show", ["All", "Eligible", "Needs review", "Not eligible"], horizontal=True, key="pg_show")
    level = c3.selectbox("Level", ALL + LEVELS, key="pg_level")
    rows = [c for c in cards if (show_ == "All" or c["decision"] == show_) and (level == "All" or c["level"] == level)
            and (not q or q in c["name"].lower() or q in c["field"].lower())]
    if not rows:
        theme.note("No programme matches these filters.")
    for c in rows:
        theme.show(card_html(c))
        with st.expander("Why this answer? Reasoning, evidence and exceptions"):
            conclusion_block(c)
            st.markdown("**Reasoning chain**")
            theme.show(chain_html(A.reasoning_chain(c["result"])))
            st.markdown("**Exception handling**")
            exceptions_block(c)
            if c["review"]["code"] != "auto":
                st.checkbox("I have dealt with this (checked my marks or confirmed with the institution)", key=f"rv_{sid}_{c['id']}")
    try:
        st.download_button("⬇️ Download PDF report", evaluation_pdf(profile, [c["result"] for c in rows or cards]),
                           "eligibility_report.pdf", "application/pdf")
    except Exception:  # report is optional; never block the page
        st.caption("PDF report is unavailable right now.")
    st.caption("Sample criteria are illustrative, not official. Confirm with the institution.")


# ------------------------------------------------------------------ 3 gaps + pathways
def page_gaps() -> None:
    profile, kb = need_profile(), common.get_kb()
    cards = A.programme_cards(profile, kb)
    theme.hero("What's missing, and other ways in", "Pick a programme to see exactly what stands between you and it, and which alternative routes exist.")
    c = pick(cards, "studio_gap_prog", "Programme", profile)
    r, a = c["result"], c["analysis"]
    theme.show(card_html(c))
    rows = []
    for k in r.conditions:
        kind, lab = theme.TRI[k.result.value]
        status = lab if k.result.value != "FALSE" else "❌ " + k.gap_text.replace(" percentage points", " points short")
        rows.append((k.label, k.student_value, k.required, theme.bar(k.student_value, k.required, k.result.value), Raw(theme.pill(status, kind))))
    theme.table(["Requirement", "You", "Needed", "Your mark vs needed (tick)", "Status"], rows)
    left, right = st.columns(2)
    with left:
        if a["information_required"]:
            st.markdown("**Add to your profile**")
            for m in dict.fromkeys(a["information_required"]):
                st.markdown(f"- {m}")
    with right:
        if a["next_steps"]:
            st.markdown("**What you can do**")
            for s in dict.fromkeys(a["next_steps"]):
                st.markdown(f"- {s}")
    if c["decision"] == "Eligible":
        st.success("Nothing is missing for this programme.")
    st.divider()
    st.subheader("Alternative pathways")
    routes = A.pathways(profile, c["id"], kb)
    if not routes:
        theme.note("No alternative route to this programme is defined in the sample knowledge base.")
    for i, p in enumerate(routes):
        with st.expander(f"{'🟢 Can start now' if p['feasible_now'] else '🟡 Not yet'}  ·  {p['name']}", expanded=(i == 0)):
            chips = [("You are here", "start")] + [(lab, "goal" if j == len(p["chain"]) - 1 else "") for j, (_, lab, _) in enumerate(p["chain"])]
            theme.show(str(theme.chain(chips)))
            st.markdown(f"*{p['type']}.* {p['why']}")
            st.markdown(f"**Entry check:** {p['why_now']}")
            if p["blocking"]:
                st.markdown("**Prerequisites still blocking the first step**")
                for lab, gap in p["blocking"]:
                    st.markdown(f"- {lab}: {gap}")
            st.markdown("**Steps to complete**")
            for s in p["to_do"]:
                st.markdown(f"- {s}")
            st.caption(f"{p['recognition']} Source status: {p['verification']}. {p['disclaimer']}")
    ov = A.pathway_overview(profile, kb)
    if ov:
        with st.expander("All programmes you are not eligible for: is there a route you could start today?"):
            theme.table(["Programme", "Result", "Routes known", "Startable now"],
                        [(o["name"], o["decision"], o["routes"], ", ".join(o["ready"]) or "None") for o in ov])
    st.divider()
    what_if(profile, kb)


def what_if(profile: dict, kb: dict) -> None:
    st.subheader("🎛️ Try it: what if my marks were higher?")
    st.caption("Hypothetical only. Your saved profile never changes, and only sliders you move are simulated.")
    sid = profile["student_id"]
    spec = [("Overall %", "overall_pct", profile.get("overall_pct")), ("Mathematics %", "mathematics", profile["marks"].get("mathematics")),
            ("Physics %", "physics", profile["marks"].get("physics")), ("Chemistry %", "chemistry", profile["marks"].get("chemistry"))]
    cols, over, marks = st.columns(4), {}, {}
    for col, (label, key, cur) in zip(cols, spec):
        start = int(cur) if cur is not None else 50
        v = col.slider(label, 0, 100, start, key=f"wi_{sid}_{key}")
        if v != start:
            (over if key == "overall_pct" else marks)[key] = v
    if not over and not marks:
        st.info("Move a slider to see which programmes would change.")
        return
    sim = simulate(profile, {**over, "marks": marks}, kb)
    a, b = st.columns(2)
    a.success("Newly eligible: " + (", ".join(sim["newly_eligible"]) or "none"))
    b.warning("No longer eligible: " + (", ".join(sim["no_longer_eligible"]) or "none"))
    changed = [(x["Programme"], x["Current"], x["Hypothetical"]) for x in sim["rows"] if x["Changed"] == "Yes"]
    if changed:
        theme.table(["Programme", "Now", "If marks changed"], changed)
    if sim["remaining_failed"]:
        with st.expander("Still not met even with these marks"):
            for name, items in sim["remaining_failed"].items():
                st.markdown(f"**{name}**: " + "; ".join(f"{l} ({g})" for l, g in items))


# ------------------------------------------------------------------ 4 reasoning
def page_reasoning() -> None:
    profile, kb = need_profile(), common.get_kb()
    cards = A.programme_cards(profile, kb)
    theme.hero("How each answer was reached", "Rule, your input, evidence and result for every condition. Nothing is a black box.")
    c = pick(cards, "studio_reason_prog", "Programme", profile, prefer_open=False)
    r = c["result"]
    theme.show(card_html(c))
    conclusion_block(c)
    t1, t2, t3, t4 = st.tabs(["🔗 Reasoning chain", "📎 Evidence & rule", "⚠️ Exceptions", "⚖️ vs simple if/else"])
    with t1:
        theme.show(chain_html(A.reasoning_chain(r)))
    with t2:
        src = r.source or {}
        st.markdown("**Rule used**")
        st.code(r.rule_expression, language=None)
        theme.table(["Item", "Value"], [("Rule version", f"v{r.rule_version}"), ("Source", src.get("name", "unknown")),
                                        ("Verification", src.get("verification_status", "Unverified")),
                                        ("Verified on", src.get("verified_on") or "Not verified")])
        st.markdown("**Evidence per condition**")
        theme.table(["Condition", "Evidence"], [(k.label, k.evidence) for k in r.conditions])
    with t3:
        exceptions_block(c)
    with t4:
        cmp_ = A.baseline_comparison(profile, kb)
        diff = [x for x in cmp_ if not x["agree"]]
        st.markdown(f"On your profile the simple if/else baseline gives a different answer from the rule engine for **{len(diff)} of {len(cmp_)}** programmes.")
        theme.table(["Programme", "Rule engine", "Simple if/else", "What differs"],
                    [(x["name"], x["engine"], x["baseline"], x["note"]) for x in sorted(cmp_, key=lambda x: x["agree"])])
        st.caption("The baseline checks only overall %, subject minimums and stream, and treats blanks as zero.")


# ------------------------------------------------------------------ 5 quality + KB
def page_quality() -> None:
    kb = common.get_kb()
    theme.hero("Is the system right?", "The knowledge base, documented test cases, and measured results against a simple baseline.")
    s = A.kb_summary(kb)
    theme.stats([(s["programmes"], "Programmes", "aps-in"), (s["rules"], "Rules encoded", "aps-in"), (s["routes"], "Alternative routes", "aps-in"),
                 (s["certificates"], "Certificates", "aps-in")])
    t1, t2, t3 = st.tabs(["📚 Knowledge base", "🧪 Test cases", "📊 Measured results"])
    with t1:
        st.markdown("**Documented assumptions**")
        for a_ in A.ASSUMPTIONS:
            st.markdown(f"- {a_}")
        st.markdown("**Coverage**: " + ", ".join(f"{v} {k}" for k, v in s["levels"].items()) + " · rule status: "
                    + ", ".join(f"{v} {k}" for k, v in s["verification"].items()))
        theme.table(["Programme", "Level", "Field", "Rule"],
                    [(p["name"], p["level"], p["field"], " AND ".join(k.rule for k in A.evaluate_programme(A.normalise_profile({}), p).conditions)) for p in kb["programmes"]])
    with t2:
        rows = A.run_cases(kb)
        ok = sum(1 for x in rows if x["pass"])
        st.markdown(f"**{ok} of {len(rows)} acceptance criteria met.** Each case states its assumption and the decision it must produce.")
        theme.table(["Type", "Case", "Assumption", "Must give", "Got", "Result"],
                    [(x["kind"], x["name"], x["assumption"], x["expected"], x["actual"], "✅ Pass" if x["pass"] else "❌ Fail") for x in rows])
    with t3:
        a, b, c = st.columns(3)
        n = a.number_input("Synthetic profiles", 50, 2000, 300, 50)
        seed = b.number_input("Random seed", 0, 10 ** 6, 42)
        pm = c.slider("Share of fields blanked", 0.05, 0.6, 0.25, 0.05)
        if st.button("▶️ Run measured evaluation", type="primary"):
            with st.spinner("Evaluating..."):
                st.session_state["studio_suite"] = run_suite(kb, int(n), int(seed), float(pm))
        suite = st.session_state.get("studio_suite")
        if not suite:
            st.info("Press the button to measure the rule engine against the simple baseline.")
            return
        quality_results(suite)


def quality_results(sx: dict) -> None:
    e, b, inc, cfg = sx["engine"], sx["baseline"], sx["incomplete"], sx["config"]
    st.caption(f"{cfg['n_profiles']} synthetic profiles × {cfg['programmes']} programmes = {cfg['pairs_complete']} decisions (seed {cfg['seed']}). Not real students.")
    f = lambda m: f"{m:.3f}"
    theme.table(["System", "Accuracy", "Precision", "Recall", "F1", "TP / FP / FN / TN"],
                [("Rule engine", f(e["accuracy"]), f(e["precision"]), f(e["recall"]), f(e["f1"]), f"{e['tp']} / {e['fp']} / {e['fn']} / {e['tn']}"),
                 ("Simple if/else", f(b["accuracy"]), f(b["precision"]), f(b["recall"]), f(b["f1"]), f"{b['tp']} / {b['fp']} / {b['fn']} / {b['tn']}")])
    st.markdown("**When information is missing**")
    theme.table(["Measure", "Rule engine", "Simple if/else"],
                [("Gave a definite answer", f"{inc['engine_decision_rate']:.1%}", "100% (always guesses)"),
                 ("Correct when definite", f"{inc['engine_definite_accuracy']:.1%}", f"{inc['baseline_accuracy_vs_truth']:.1%}"),
                 ("False 'Eligible' answers", inc["engine_false_eligible"], inc["baseline_false_eligible"]),
                 ("Sent to Needs review", inc["engine_needs_review"], 0)])
    st.markdown("**Failure patterns**")
    st.markdown(f"- The baseline gave **{b['fp']}** false 'Eligible' answers on complete profiles. It ignores entrance exams, qualifications and OR-rules.\n"
                f"- With blanks it gave **{inc['baseline_false_eligible']}** false 'Eligible' answers; the engine gave **{inc['engine_false_eligible']}**.\n"
                f"- The engine never answers wrongly when it answers, but it holds back **{1 - inc['engine_decision_rate']:.1%}** of incomplete cases for review.")
    st.markdown("**Trade-offs**")
    st.markdown("- Caution vs speed: Needs review is slower than a guess but never wrongly tells someone they qualify.\n"
                "- Transparency vs flexibility: every rule is hand-written and explainable, so new rules cost maintenance effort.\n"
                "- A 1.000 score only shows the engine follows the sample rules faithfully (the reference uses the same rules). It does not prove real-world correctness.")
    rc, ec, tm = sx["rule_coverage"], sx["explanation_completeness"], sx["timing_ms"]
    st.caption(f"Rule coverage {rc['rules_exercised']}/{rc['rules_total']} (both outcomes seen: {rc['rules_with_true_and_false']}) · explanation completeness "
               f"{ec['mean']:.0%} · about {tm['mean_per_programme']:.2f} ms per programme (machine-dependent).")
