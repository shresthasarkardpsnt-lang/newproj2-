"""Alternative academic routes: prerequisite checking against the student's profile + NetworkX graphs."""
from __future__ import annotations
import copy
import textwrap
from typing import Optional

import networkx as nx

from .constants import ELIGIBLE, NEEDS_REVIEW, NOT_ELIGIBLE
from .eligibility import EvaluationResult, evaluate_programme
from .kb import cert_by_id, cert_names, prog_by_id
from .validation import default_profile, normalise_profile

RANK = {ELIGIBLE: 0, NEEDS_REVIEW: 1, NOT_ELIGIBLE: 2}
NO_GUARANTEE = ("An alternative route never guarantees admission. Institutions decide admissions, and "
                "recognition of any route must be confirmed with them.")


def entry_programme(route: dict, kb: dict) -> Optional[dict]:
    """The programme-like object whose requirements gate the first step of a route."""
    if route.get("entry_requirements"):
        return {"id": route["id"], "name": "Entry requirements of this route", "level": "Route", "field": "",
                "requirements": route["entry_requirements"], "rule_version": route.get("rule_version", 1),
                "source": route.get("source", {})}
    if route.get("entry_programme"):
        base = copy.deepcopy(prog_by_id(kb, route["entry_programme"]))
        if base is None:
            return None
        repl = route.get("replace_requirements") or {}
        base["requirements"] = [repl.get(r["id"], r) for r in base["requirements"]]
        if repl:
            base["name"] += " (with route-specific entrance exam)"
        return base
    return None


def _rules_of(prog: dict) -> list:
    return [c.rule for c in evaluate_programme(default_profile(), prog).conditions]


def evaluate_route(profile: dict, route: dict, kb: dict) -> dict:
    profile = normalise_profile(profile)
    names = cert_names(kb)
    entry = entry_programme(route, kb)
    entry_res: Optional[EvaluationResult] = evaluate_programme(profile, entry, names) if entry else None
    steps, first_prog_seen = [], False
    for i, s in enumerate(route["steps"], 1):
        kind = s.get("kind")
        d = {"index": i, "kind": kind, "label": s.get("label", ""), "requirements": [], "status": "", "note": ""}
        if kind == "programme":
            prog = prog_by_id(kb, s["programme_id"])
            d["label"] = d["label"] or (prog or {}).get("name", s["programme_id"])
            d["requirements"] = _rules_of(prog) if prog else []
            d["verification"] = (prog or {}).get("source", {}).get("verification_status", "Unverified")
            if not first_prog_seen and entry_res is not None and entry and entry.get("id") != route["id"]:
                d["status"] = f"Current eligibility to start: {entry_res.decision}"
            elif not first_prog_seen:
                d["status"] = "First step"
            else:
                d["status"] = "Later step - requirements apply after completing earlier steps"
            first_prog_seen = True
        elif kind == "certificate":
            c = cert_by_id(kb, s["certificate_id"])
            d["label"] = d["label"] or (c or {}).get("name", s["certificate_id"])
            d["status"] = "Certificate step"
            d["note"] = (c or {}).get("recognition_status", "")
            d["verification"] = (c or {}).get("verification_status", "Unverified")
        else:
            d["status"] = "Required step"
        steps.append(d)
    decision = entry_res.decision if entry_res else "No entry check defined"
    missing = (entry_res.failed + entry_res.unknown) if entry_res else []
    if entry_res is None:
        why_now = "This route has no machine-checkable entry requirement."
    elif decision == ELIGIBLE:
        why_now = "You currently meet every entry requirement for the first step of this route."
    elif decision == NEEDS_REVIEW:
        why_now = f"No entry requirement is failed, but {len(entry_res.unknown)} cannot be checked until you provide more information."
    else:
        why_now = f"{len(entry_res.failed)} entry requirement(s) are not currently met."
    src = route.get("source", {})
    final = prog_by_id(kb, route["final_programme"])
    return {
        "route": route, "id": route["id"], "name": route["name"], "route_type": route.get("route_type", ""),
        "entry": entry_res, "entry_decision": decision, "missing": missing, "steps": steps,
        "why": route.get("why_recommended", ""), "why_now": why_now,
        "steps_to_complete": route.get("steps_to_complete", []),
        "duration": route.get("typical_duration") or "Not verified", "cost": route.get("cost") or "Not verified",
        "officially_recognised": route.get("officially_recognised", "Unverified"),
        "recognition_note": route.get("recognition_note", ""),
        "source": src, "verification_status": src.get("verification_status", "Unverified"),
        "final_programme": (final or {}).get("name", route["final_programme"]),
        "disclaimer": NO_GUARANTEE,
    }


def find_routes(profile: dict, target_id: str, kb: dict) -> list:
    routes = [r for r in kb["routes"] if target_id in r.get("alternative_for", []) or r.get("final_programme") == target_id]
    evaluated = [evaluate_route(profile, r, kb) for r in routes]
    evaluated.sort(key=lambda e: (RANK.get(e["entry_decision"], 3), len(e["entry"].failed) if e["entry"] else 99, e["name"]))
    return evaluated


# --------------------------------------------------------------------- graphs
def build_route_graph(route_eval: dict, preferred_name: Optional[str] = None) -> nx.DiGraph:
    G = nx.DiGraph()
    G.add_node("start", label="Current Profile", ntype="profile")
    prev = "start"
    steps = route_eval["steps"]
    for i, s in enumerate(steps):
        nid = f"s{i}"
        last = i == len(steps) - 1
        ntype = ("target" if last and s["kind"] == "programme" else
                 {"certificate": "certificate", "exam": "exam"}.get(s["kind"], "qualification"))
        label = s["label"]
        if i == 0 and route_eval["entry"] is not None and s["kind"] == "programme":
            label += f"\n[{route_eval['entry_decision']}]"
        G.add_node(nid, label=label, ntype=ntype)
        G.add_edge(prev, nid, style="solid")
        prev = nid
    if preferred_name and preferred_name != route_eval["final_programme"]:
        G.add_node("pref", label=f"Preferred: {preferred_name}", ntype="preferred")
        G.add_edge(prev, "pref", style="dashed")
    return G


NODE_COLOURS = {"profile": "#cfe8ff", "qualification": "#ffe8b3", "certificate": "#e3d4f7",
                "exam": "#e6e6e6", "target": "#c9f0d2", "preferred": "#ffffff"}


def draw_graph(G: nx.DiGraph, title: str = ""):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pos = {n: (i, 0) for i, n in enumerate(nx.topological_sort(G))}
    n = len(pos)
    fig, ax = plt.subplots(figsize=(max(7, 2.6 * n), 2.4))
    for u, v, d in G.edges(data=True):
        ax.annotate("", xy=pos[v], xytext=pos[u], zorder=1,
                    arrowprops=dict(arrowstyle="-|>", lw=1.6, color="#555", shrinkA=32, shrinkB=32,
                                    linestyle="--" if d.get("style") == "dashed" else "-"))
    for node, d in G.nodes(data=True):
        ax.text(*pos[node], textwrap.fill(d["label"].replace("\n", " "), 20), ha="center", va="center", fontsize=9, zorder=2,
                bbox=dict(boxstyle="round,pad=0.5", fc=NODE_COLOURS.get(d["ntype"], "#fff"), ec="#444"))
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(-0.6, 0.6)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=10)
    fig.tight_layout()
    return fig


LAYER = {"Foundation": 0, "Diploma": 1, "UG": 2, "PG": 3}


def progression_graph(kb: dict) -> nx.DiGraph:
    G = nx.DiGraph()
    for p in kb["programmes"]:
        G.add_node(p["id"], label=p["name"], layer=LAYER.get(p["level"], 2), level=p["level"])
    ids = set(G.nodes)
    for p in kb["programmes"]:
        for t in p.get("progression_to", []):
            if t in ids:
                G.add_edge(p["id"], t)
    return G


def draw_progression(G: nx.DiGraph):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pos = nx.multipartite_layout(G, subset_key="layer", align="vertical")
    fig, ax = plt.subplots(figsize=(11, 7))
    colours = {"Foundation": "#ffe8b3", "Diploma": "#e3d4f7", "UG": "#cfe8ff", "PG": "#c9f0d2"}
    nx.draw_networkx_edges(G, pos, ax=ax, arrows=True, arrowstyle="-|>", node_size=3200, edge_color="#666")
    for node, (x, y) in pos.items():
        ax.text(x, y, textwrap.fill(G.nodes[node]["label"], 22), ha="center", va="center", fontsize=7.5,
                bbox=dict(boxstyle="round,pad=0.4", fc=colours.get(G.nodes[node]["level"], "#fff"), ec="#444"))
    ax.axis("off")
    ax.margins(0.15)
    fig.tight_layout()
    return fig
