import subprocess
import sys

import pandas as pd
import streamlit as st

from engine.constants import ROOT
from engine.evaluation import run_suite
from . import common


def render():
    st.title("🧪 Testing & Performance")
    kb = common.get_kb()
    st.caption("Measured live on seeded synthetic profiles. Ground truth is an independent reference implementation. "
               "These are not real student outcomes, and nothing here is hard-coded.")
    c1, c2, c3 = st.columns(3)
    n = c1.number_input("Synthetic profiles", 50, 2000, 300, 50)
    seed = c2.number_input("Random seed", 0, 10**6, 42)
    pm = c3.slider("Share of fields blanked (incomplete-data test)", 0.05, 0.6, 0.25, 0.05)
    if st.button("▶️ Run evaluation suite", type="primary"):
        with st.spinner("Evaluating..."):
            st.session_state["suite"] = run_suite(kb, int(n), int(seed), float(pm))
    s = st.session_state.get("suite")
    if s:
        cfg = s["config"]
        st.write(f"{cfg['n_profiles']} profiles × {cfg['programmes']} programmes = {cfg['pairs_complete']} decisions (seed {cfg['seed']}).")
        e, b = s["engine"], s["baseline"]
        st.subheader("Complete profiles: rule engine vs simple if/else baseline")
        st.dataframe(pd.DataFrame([{"System": n_, "Accuracy": f"{m['accuracy']:.3f}", "Precision": f"{m['precision']:.3f}",
                                    "Recall": f"{m['recall']:.3f}", "F1": f"{m['f1']:.3f}", "TP": m["tp"], "FP": m["fp"], "FN": m["fn"], "TN": m["tn"]}
                                   for n_, m in (("Rule engine", e), ("If/else baseline", b))]), hide_index=True)
        st.caption("Positive class = Eligible. Baseline checks only overall %, subject minimums and stream, and treats missing values as 0.")
        inc = s["incomplete"]
        st.subheader("Incomplete profiles (missing-information handling)")
        a, b2, c = st.columns(3)
        a.metric("Engine: definite decisions", f"{inc['engine_decision_rate']:.1%}")
        b2.metric("Engine: wrong definite decisions", inc["engine_wrong_definite"])
        c.metric("Baseline accuracy vs truth", f"{inc['baseline_accuracy_vs_truth']:.1%}")
        st.write(f"Engine returned 'Needs review' for {inc['engine_needs_review']} of {inc['pairs']} cases instead of guessing; "
                 f"false 'Eligible' outcomes: engine {inc['engine_false_eligible']}, baseline {inc['baseline_false_eligible']}.")
        rc, ec, tm = s["rule_coverage"], s["explanation_completeness"], s["timing_ms"]
        st.subheader("Rule coverage, explanation completeness and speed")
        a, b2, c = st.columns(3)
        a.metric("Rules exercised", f"{rc['rules_exercised']}/{rc['rules_total']}")
        b2.metric("Rules seen both TRUE and FALSE", f"{rc['rules_with_true_and_false']}/{rc['rules_total']}")
        c.metric("Explanation completeness", f"{ec['mean']:.1%}")
        st.write(f"Mean evaluation time: {tm['mean_per_programme']:.3f} ms per programme (p95 {tm['p95_per_programme']:.3f} ms); "
                 f"{tm['mean_per_student_all_programmes']:.2f} ms per student across all programmes. Timing is machine-dependent.")
        with st.expander("Per-rule coverage"):
            st.dataframe(pd.DataFrame(rc["rows"]), hide_index=True)
        for note in s["notes"]:
            st.caption(note)
    st.divider()
    st.subheader("Automated tests (pytest)")
    if st.button("Run pytest -q"):
        with st.spinner("Running tests (this can take a minute)..."):
            proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "--no-header"], cwd=ROOT, capture_output=True, text=True, timeout=600)
        st.code(proc.stdout[-6000:] + proc.stderr[-2000:])
        (st.success if proc.returncode == 0 else st.error)("All tests passed." if proc.returncode == 0 else "Some tests failed.")
