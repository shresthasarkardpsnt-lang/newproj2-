import copy
from conftest import make_profile
from engine.certificates import cert_flags, certificate_impact, recommend
from engine.constants import CERT_CATEGORIES
from engine.eligibility import evaluate_all
from engine.pathway import NO_GUARANTEE, build_route_graph, evaluate_route, find_routes
from engine.kb import route_by_id
from engine.simulator import simulate
from engine.roadmap import build_roadmap


# ---------------------------------------------------------------- routes
def test_routes_check_prerequisites(kb):
    r = route_by_id(kb, "r_found_bca")  # foundation needs overall >= 40
    ok = evaluate_route(make_profile(overall_pct=45), r, kb)
    bad = evaluate_route(make_profile(overall_pct=35), r, kb)
    assert ok["entry_decision"] == "Eligible" and bad["entry_decision"] == "Not eligible"
    assert bad["missing"] and bad["missing"][0].gap == 5


def test_route_inline_entry_requirements_and_alt_entrance(kb):
    mca = evaluate_route(make_profile(bachelor={"has": False}), route_by_id(kb, "r_mca_bridge"), kb)
    assert mca["entry_decision"] == "Not eligible"
    cet = evaluate_route(make_profile(entrance_exams={"State CET": {"status": "Qualified"}}), route_by_id(kb, "r_cet_cse"), kb)
    assert cet["entry_decision"] == "Eligible"
    jee_only = evaluate_route(make_profile(entrance_exams={"JEE Main": {"status": "Qualified"}}), route_by_id(kb, "r_cet_cse"), kb)
    assert jee_only["entry_decision"] != "Eligible"  # route requires State CET


def test_route_never_claims_guarantee_or_verified_recognition(kb, weak):
    for e in find_routes(weak, "btech_cse", kb):
        assert e["officially_recognised"] != "Verified - recognised"
        assert e["duration"] == "Not verified" and e["cost"] == "Not verified"
        assert "never guarantees" in e["disclaimer"] and NO_GUARANTEE == e["disclaimer"]


def test_routes_sorted_by_current_eligibility(kb, weak):
    order = [e["entry_decision"] for e in find_routes(weak, "btech_cse", kb)]
    rank = {"Eligible": 0, "Needs review": 1, "Not eligible": 2}
    assert [rank[o] for o in order] == sorted(rank[o] for o in order)


def test_route_graph_structure(kb, weak):
    e = evaluate_route(weak, route_by_id(kb, "r_diploma_lateral"), kb)
    G = build_route_graph(e, "B.Tech CSE")
    assert G.nodes["start"]["label"] == "Current Profile"
    assert list(G.successors("start")) == ["s0"] and G.out_degree("s1") == 1


# ---------------------------------------------------------------- certificates
def test_certificate_never_changes_marks_or_eligibility_unless_named(kb, weak):
    for c in kb["certificates"]:
        imp = certificate_impact(weak, c["id"], kb)
        assert imp["marks_unchanged"]
        named = bool(cert_flags(c, kb)["formal_programmes"])
        if not named:
            assert imp["changes"] == [], c["id"]


def test_named_certificate_changes_only_the_programme_that_names_it(kb):
    p = make_profile(bachelor={"has": True, "discipline": "Commerce", "pct": 60}, studied={"mathematics": False}, marks={"mathematics": None},
                     entrance_exams={"NIMCET": {"status": "Qualified", "score": 80}})
    imp = certificate_impact(p, "math_bridge_univ", kb)
    assert [c["programme"] for c in imp["changes"]] == ["Master of Computer Applications (MCA)"]
    assert imp["changes"][0]["after"] == "Eligible"


def test_recommendations_structure_and_categories(kb, weak):
    weak["career_interests"] = ["Artificial intelligence"]
    recs = recommend(weak, kb, "btech_aiml")
    assert recs
    for r in recs:
        assert r["category"] in CERT_CATEGORIES
        for k in ("name", "issuer", "skills", "reasons", "recognition_status", "evidence_source", "verification_status"):
            assert r[k]
        assert r["duration_display"] == "Not verified"  # nothing is claimed verified
        assert "probability" not in " ".join(r["reasons"]).lower()
    assert {r["category"] for r in recs} >= {"Academic preparation courses"}


def test_completed_certificates_excluded_and_dataset_has_no_verified_claims(kb, weak):
    weak["certificates"] = ["khan_math"]
    assert "khan_math" not in [r["id"] for r in recommend(weak, kb, "btech_cse")]
    assert all(c["verification_status"] != "Verified" for c in kb["certificates"])


def test_all_four_categories_present_in_data(kb):
    assert {c["category"] for c in kb["certificates"]} == set(CERT_CATEGORIES)


# ---------------------------------------------------------------- simulator
def test_simulation_does_not_modify_profile(kb, weak):
    before = copy.deepcopy(weak)
    sim = simulate(weak, {"overall_pct": 99, "marks": {"mathematics": 99}, "stream": "Commerce",
                          "entrance_exams": {"JEE Main": {"status": "Qualified"}}}, kb)
    assert weak == before and sim["profile_unchanged"] and "HYPOTHETICAL" in sim["label"]
    assert sim["hypothetical_profile"]["overall_pct"] == 99


def test_simulation_newly_eligible_and_transitions(kb, weak):
    sim = simulate(weak, {"overall_pct": 66, "marks": {"mathematics": 62}, "entrance_exams": {"JEE Main": {"status": "Qualified"}}}, kb)
    assert "B.Tech Computer Science & Engineering" in sim["newly_eligible"]
    t = [x for x in sim["false_to_true"] if x["Programme"].startswith("B.Tech Computer") and x["Condition"].startswith("Mathematics")]
    assert t and t[0]["From"] == "FALSE" and t[0]["To"] == "TRUE"


def test_simulation_with_no_overrides_changes_nothing(kb, weak):
    sim = simulate(weak, {}, kb)
    assert not sim["newly_eligible"] and not sim["transitions"]


def test_simulation_can_lose_eligibility(kb, strong):
    sim = simulate(strong, {"overall_pct": 40}, kb)
    assert sim["no_longer_eligible"]


# ---------------------------------------------------------------- roadmap
def test_roadmap_progress_does_not_change_eligibility(kb, weak):
    rm0 = build_roadmap(weak, kb, "btech_cse", set())
    keys = {i["key"] for s in rm0["stages"] for i in s["items"]}
    certs = [i["cert_id"] for s in rm0["stages"] for i in s["items"] if "cert_id" in i]
    rm1 = build_roadmap({**weak, "certificates": certs}, kb, "btech_cse", keys)
    assert rm1["progress"] == 1.0 and rm1["decision"] == rm0["decision"] == "Not eligible"
    assert [s["stage"] for s in rm0["stages"]] == [1, 2, 3, 4, 5, 6, 7]
