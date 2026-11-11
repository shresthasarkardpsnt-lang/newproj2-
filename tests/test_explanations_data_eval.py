import ast
import re
from pathlib import Path

from conftest import ROOT, make_profile
from engine.eligibility import evaluate_all
from engine.evaluation import baseline_eligible, generate_profiles, reference_eligible, run_suite
from engine.explain import explain_result, explanation_completeness, explanation_markdown
from engine.kb import validate_kb


def test_every_decision_has_complete_explanation(kb, weak):
    partial = make_profile(overall_pct=None, marks={"mathematics": None}, stream=None, entrance_exams={})
    for prof in (weak, partial, make_profile()):
        for r in evaluate_all(prof, kb):
            score, gaps = explanation_completeness(r)
            assert score == 1.0, (r.programme_id, gaps)
            e = explain_result(r)
            assert e["final_decision"] and e["final_explanation"] and e["rule_expression"]
            for c in e["conditions"]:
                assert all(c[k] for k in ("student_input", "requirement", "logical_rule", "result", "evidence", "explanation"))
                if c["result"] == "UNKNOWN":
                    assert c["missing_information"]


def test_explanation_shows_rule_and_values(kb, weak):
    r = next(x for x in evaluate_all(weak, kb) if x.programme_id == "btech_cse")
    md = explanation_markdown(r)
    assert "Overall >= 65" in md and "58%" in md and "[FALSE]" in md and "Not eligible" in md


def test_no_fake_confidence_in_outputs(kb, weak):
    text = " ".join(explanation_markdown(r) for r in evaluate_all(weak, kb)).lower()
    assert "confidence" not in text and "probability" not in text and "%  chance" not in text


def test_knowledge_base_is_valid_and_honest(kb):
    assert validate_kb(kb) == []
    for p in kb["programmes"]:
        assert p["source"]["verification_status"] == "Illustrative sample" and p["source"]["verified_on"] is None
        assert "NOT an official" in p["source"]["name"]
    for r in kb["routes"]:
        assert r["officially_recognised"] == "Unverified" and r["typical_duration"] is None and r["cost"] is None
    ids = [p["id"] for p in kb["programmes"]]
    assert len(ids) == len(set(ids)) and {"btech_cse", "btech_aiml", "btech_it", "btech_ece", "bca", "bsc_cs", "bsc_ds", "mca"} <= set(ids)


def test_evaluation_suite_is_reproducible_and_sound(kb):
    a, b = run_suite(kb, 80, seed=7), run_suite(kb, 80, seed=7)
    for k in ("engine", "baseline", "incomplete", "rule_coverage", "explanation_completeness"):
        x, y = a[k], b[k]
        if k == "explanation_completeness":
            assert x == y
        elif k == "rule_coverage":
            assert x["rows"] == y["rows"]
        else:
            assert x == y
    assert a["engine"]["fp"] == 0 and a["engine"]["fn"] == 0
    assert a["engine_needs_review_on_complete"] == 0
    assert a["incomplete"]["engine_wrong_definite"] == 0 and a["incomplete"]["engine_false_eligible"] == 0
    assert a["explanation_completeness"]["mean"] == 1.0
    assert a["baseline"]["accuracy"] < a["engine"]["accuracy"]
    assert a["rule_coverage"]["exercised_ratio"] == 1.0


def test_reference_oracle_and_baseline_differ_where_expected(kb):
    profiles = generate_profiles(kb, 60, 3)
    lat = next(p for p in kb["programmes"] if p["id"] == "btech_lateral_cse")
    # baseline ignores qualification rules, so it says Eligible for everyone here
    assert all(baseline_eligible(p, lat) for p in profiles)
    assert not all(reference_eligible(p, lat) for p in profiles)


def test_no_chatbot_or_external_llm_present():
    forbidden = ["openai", "anthropic", "google.generativeai", "genai", "langchain", "chat_input", "chat_message", "ollama", "huggingface"]
    for f in list(Path(ROOT).rglob("*.py")) + [ROOT / "requirements.txt"]:
        if "tests" in f.parts or ".venv" in f.parts:
            continue
        text = f.read_text(encoding="utf-8").lower()
        for word in forbidden:
            assert word not in text, f"{word} found in {f}"
    reqs = (ROOT / "requirements.txt").read_text().lower()
    assert "requests" not in reqs and "httpx" not in reqs
    for f in Path(ROOT).rglob("*.py"):
        if "tests" in f.parts:
            continue
        tree = ast.parse(f.read_text(encoding="utf-8"))
        mods = {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module} | \
               {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        assert not mods & {"requests", "urllib3", "httpx", "socket", "aiohttp"}, f
