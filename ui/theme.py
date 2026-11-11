"""Look and feel: one stylesheet plus tiny HTML helpers. Plain HTML only (no interactive tables or charts).

Every dynamic string goes through `esc`, so student names or rule text can never inject markup.
Colours use translucent tints so the page reads well in both light and dark Streamlit themes.
"""
from __future__ import annotations

import html

import streamlit as st


class Raw(str):
    """Marks a string as already-safe HTML."""


def esc(x) -> str:
    return x if isinstance(x, Raw) else html.escape("" if x is None else str(x))


CSS = """
<style>
:root{--ink:#1B2B34;--muted:#5B6B73;--teal:#0B4F5C;--teal2:#13808F;--coral:#E2552F;--gold:#F4B942;--cream:#F6F1E9;--mint:#E4EFEC;
--ok:#1E9E6A;--rv:#E9A23B;--no:#D6455D;--line:rgba(11,79,92,.16);--shadow:0 6px 18px rgba(11,79,92,.10)}
.stApp{background:var(--cream);color:var(--ink)}
.block-container{max-width:1120px;padding-top:1.2rem;padding-bottom:4rem}
h1,h2,h3,.aps-hero h1,.aps-card h4,.aps-brand{font-family:Georgia,'Times New Roman',serif!important;letter-spacing:-.01em}
h2,h3{color:var(--teal)!important}
section[data-testid="stSidebar"]{background:var(--mint);border-right:1px solid var(--line)}
.aps-brand{font-size:1.45rem;font-weight:700;color:var(--teal);margin:0 0 2px 0}.aps-brandsub{font-size:.82rem;color:var(--muted);margin-bottom:12px}
.aps-hero{position:relative;overflow:hidden;background:linear-gradient(135deg,#0B4F5C 0%,#13808F 70%,#2BB1A6 120%);color:#fff;border-radius:24px;padding:30px 34px;margin-bottom:16px;box-shadow:var(--shadow)}
.aps-hero:before{content:"";position:absolute;right:-60px;top:-70px;width:240px;height:240px;border-radius:50%;background:radial-gradient(circle,rgba(244,185,66,.55),rgba(244,185,66,0) 70%)}
.aps-hero:after{content:"";position:absolute;right:120px;bottom:-90px;width:200px;height:200px;border-radius:50%;background:radial-gradient(circle,rgba(226,85,47,.45),rgba(226,85,47,0) 70%)}
.aps-hero h1{position:relative;margin:0 0 6px 0;font-size:2rem;color:#fff!important;padding:0}
.aps-hero p{position:relative;margin:0;opacity:.92;font-size:1rem;max-width:720px}
.aps-badge{position:relative;display:inline-block;background:var(--gold);color:#3b2a00;font-weight:700;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;border-radius:99px;padding:3px 12px;margin-bottom:10px}
.aps-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin:10px 0 18px}
.aps-stat{display:flex;align-items:center;gap:14px;background:#fff;border-radius:18px;padding:14px 16px;border:1px solid var(--line);box-shadow:var(--shadow)}
.aps-stat .ic{flex:0 0 42px;height:42px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;color:#fff;font-weight:700}
.aps-stat b{display:block;font-family:Georgia,serif;font-size:1.9rem;line-height:1;color:var(--ink)}.aps-stat span.l{font-size:.82rem;color:var(--muted)}
.aps-ok .ic{background:var(--ok)}.aps-rv .ic{background:var(--rv)}.aps-no .ic{background:var(--no)}.aps-in .ic{background:var(--teal2)}
.aps-card{display:flex;gap:18px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:20px;padding:16px 20px;margin:12px 0 4px;box-shadow:var(--shadow);position:relative;overflow:hidden}
.aps-card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:6px}
.aps-card.ok:before{background:var(--ok)}.aps-card.no:before{background:var(--no)}.aps-card.rv:before{background:var(--rv)}
.aps-body{flex:1;min-width:0}
.aps-card h4{margin:0 0 2px 0;font-size:1.15rem;color:var(--teal)}
.aps-sub{font-size:.84rem;color:var(--muted);margin-bottom:6px}
.aps-ring{flex:0 0 74px;height:74px;border-radius:50%;background:conic-gradient(var(--c) calc(var(--p)*1%),rgba(11,79,92,.12) 0);display:flex;align-items:center;justify-content:center;position:relative}
.aps-ring:before{content:"";position:absolute;inset:8px;border-radius:50%;background:#fff}
.aps-ring b{position:relative;font-family:Georgia,serif;font-size:1.05rem;color:var(--ink)}
.aps-pill{display:inline-block;border-radius:999px;padding:3px 12px;font-size:.76rem;font-weight:700;margin:2px 6px 2px 0;border:1px solid transparent}
.p-ok{background:#DDF3EA;color:#0F6B47}.p-no{background:#FBE1E5;color:#9A2336}.p-rv{background:#FCEBCB;color:#8A5A07}.p-in{background:#D9EEF1;color:#0B4F5C}.p-mu{background:#ECE7DE;color:#4B5560}
.aps-meter{height:8px;border-radius:99px;background:rgba(11,79,92,.12);overflow:hidden;margin:8px 0 2px;display:flex}
.aps-meter i{display:block;height:100%}.m-ok{background:var(--ok)}.m-no{background:var(--no)}.m-rv{background:var(--rv)}
.aps-table{width:100%;border-collapse:separate;border-spacing:0;font-size:.9rem;margin:8px 0 14px;background:#fff;border-radius:16px;overflow:hidden;border:1px solid var(--line);box-shadow:var(--shadow)}
.aps-table th{text-align:left;padding:11px 14px;background:var(--teal);color:#fff;font-weight:600;font-size:.82rem;letter-spacing:.03em}
.aps-table td{padding:10px 14px;border-bottom:1px solid rgba(11,79,92,.10);vertical-align:top}
.aps-table tr:nth-child(even) td{background:#FAF7F1}.aps-table tr:last-child td{border-bottom:none}
.aps-bar{position:relative;height:10px;border-radius:99px;background:rgba(11,79,92,.13);min-width:120px;margin-top:5px}
.aps-bar i{position:absolute;left:0;top:0;bottom:0;border-radius:99px}.aps-bar u{position:absolute;top:-5px;bottom:-5px;width:3px;background:var(--ink);border-radius:2px}
.aps-chain{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:10px 0}
.aps-chip{border-radius:999px;padding:7px 15px;font-size:.84rem;background:#fff;border:1px solid var(--line);box-shadow:0 2px 6px rgba(11,79,92,.08)}
.aps-chip.start{background:var(--gold);border-color:var(--gold);color:#3b2a00;font-weight:700}.aps-chip.goal{background:var(--teal);color:#fff;border-color:var(--teal);font-weight:700}
.aps-arrow{color:var(--coral);font-weight:700}
.aps-step{position:relative;display:flex;gap:14px;margin:12px 0;padding:12px 16px;border-radius:16px;background:#fff;border:1px solid var(--line);box-shadow:0 2px 8px rgba(11,79,92,.07)}
.aps-num{flex:0 0 30px;height:30px;border-radius:50%;background:var(--coral);color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center;font-size:.86rem}
.aps-step small{display:block;color:var(--muted);margin-top:3px;font-size:.82rem}.aps-step code{font-size:.78rem;background:#F1ECE2;color:var(--teal);padding:1px 6px;border-radius:6px}
.aps-note{border-radius:16px;padding:12px 16px;background:#FFF4DA;border:1px solid #F1D48A;border-left:6px solid var(--gold);font-size:.9rem;margin:10px 0;color:#4a3a10}
.aps-note.info{background:#E3F3F4;border-color:#A9D6DA;border-left-color:var(--teal2);color:#0B3E47}
.aps-flow{display:flex;gap:8px;margin:2px 0 10px;flex-wrap:wrap}
.aps-flow span{flex:1;min-width:120px;text-align:center;padding:7px 4px;border-radius:999px;font-size:.82rem;background:#fff;border:1px solid var(--line);color:var(--muted)}
.aps-flow span.on{background:var(--teal);color:#fff;font-weight:700}
div[data-testid="stRadio"] [role="radiogroup"]{gap:8px;flex-wrap:wrap}
div[data-testid="stRadio"] label[data-baseweb="radio"]{background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 16px;margin:0;transition:all .15s ease;box-shadow:0 2px 6px rgba(11,79,92,.06)}
div[data-testid="stRadio"] label[data-baseweb="radio"]>div:first-child{display:none}
div[data-testid="stRadio"] label[data-baseweb="radio"]:hover{border-color:var(--teal2);transform:translateY(-1px)}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked){background:var(--teal);border-color:var(--teal)}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) *{color:#fff!important;font-weight:700}
button[data-baseweb="tab"]{font-weight:600;border-radius:12px 12px 0 0}
div[data-baseweb="tab-highlight"]{background:var(--coral)!important;height:3px!important}
div[data-testid="stExpander"]{background:#fff;border:1px solid var(--line)!important;border-radius:16px!important;box-shadow:0 2px 8px rgba(11,79,92,.06);margin-bottom:6px}
div[data-testid="stExpander"] summary{font-weight:600;color:var(--teal)}
.stButton>button,.stDownloadButton>button,div[data-testid="stFormSubmitButton"]>button{border-radius:999px;font-weight:700;padding:.45rem 1.4rem;border:1px solid var(--teal);transition:all .15s ease}
.stButton>button[kind="primary"],div[data-testid="stFormSubmitButton"]>button[kind="primary"]{background:var(--coral);border-color:var(--coral);color:#fff}
.stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-1px);box-shadow:var(--shadow)}
div[data-testid="stAlert"]{border-radius:14px}
hr{border-color:var(--line)!important}
/* ---- force a consistent light look even when Streamlit / the browser is in dark mode ---- */
:root,html,body,.stApp{color-scheme:light!important}
header[data-testid="stHeader"]{background:var(--cream)!important;border-bottom:1px solid var(--line)}
header[data-testid="stHeader"] *,[data-testid="stToolbar"] *{color:var(--ink)!important}
.stApp,.stApp p,.stApp li,.stApp label,.stApp [data-testid="stWidgetLabel"] *,.stApp [data-testid="stMarkdownContainer"] p,.stApp [data-testid="stMarkdownContainer"] li{color:var(--ink)}
.stApp [data-testid="stCaptionContainer"],.stApp [data-testid="stCaptionContainer"] *{color:var(--muted)!important}
.stApp [data-testid="stWidgetLabel"] p{font-weight:600;color:var(--teal)!important}
.stApp h1{color:var(--teal)!important}
div[data-baseweb="input"],div[data-baseweb="base-input"],div[data-baseweb="select"]>div,div[data-baseweb="textarea"],textarea{background:#fff!important;border-color:rgba(11,79,92,.28)!important;border-radius:12px!important}
div[data-baseweb="input"]:focus-within,div[data-baseweb="select"]>div:focus-within{border-color:var(--coral)!important;box-shadow:0 0 0 2px rgba(226,85,47,.18)!important}
input,textarea,div[data-baseweb="select"] *{color:var(--ink)!important;-webkit-text-fill-color:var(--ink)!important;background-color:transparent}
input::placeholder,textarea::placeholder{color:#8A979D!important;-webkit-text-fill-color:#8A979D!important}
div[data-baseweb="select"] svg,div[data-baseweb="input"] svg{fill:var(--teal)!important}
div[data-testid="stNumberInput"] button{background:#fff!important;color:var(--teal)!important}
div[data-baseweb="popover"],div[data-baseweb="popover"] ul,div[data-baseweb="menu"],ul[role="listbox"]{background:#fff!important}
div[data-baseweb="popover"] li,ul[role="listbox"] li,ul[role="listbox"] li *{background:#fff!important;color:var(--ink)!important;-webkit-text-fill-color:var(--ink)!important}
ul[role="listbox"] li:hover,ul[role="listbox"] li[aria-selected="true"]{background:var(--mint)!important}
div[data-testid="stForm"]{background:#fff;border:1px solid var(--line)!important;border-radius:20px;box-shadow:var(--shadow);padding:6px 10px}
.stButton>button,.stDownloadButton>button{background:#fff!important;color:var(--teal)!important;-webkit-text-fill-color:var(--teal)}
.stButton>button p,.stDownloadButton>button p{color:inherit!important}
.stButton>button[kind="primary"],div[data-testid="stFormSubmitButton"]>button,.stButton>button[kind="primary"] p,div[data-testid="stFormSubmitButton"]>button p{background:var(--coral)!important;border-color:var(--coral)!important;color:#fff!important;-webkit-text-fill-color:#fff}
.stButton>button[kind="primary"] p,div[data-testid="stFormSubmitButton"]>button p{background:transparent!important}
button[data-baseweb="tab"] p{color:var(--ink)!important}button[data-baseweb="tab"][aria-selected="true"] p{color:var(--coral)!important;font-weight:700}
div[data-testid="stExpander"] summary,div[data-testid="stExpander"] summary *{color:var(--teal)!important}
div[data-testid="stExpander"] details{background:#fff}
div[data-testid="stAlert"],div[data-testid="stAlert"] *{color:var(--ink)!important}
div[data-testid="stCheckbox"] label *,div[data-testid="stSlider"] *{color:var(--ink)}
div[data-testid="stSlider"] [data-testid="stThumbValue"]{color:var(--coral)!important;font-weight:700}
div[data-testid="stRadio"] label[data-baseweb="radio"] *{color:var(--ink)}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) *{color:#fff!important;-webkit-text-fill-color:#fff!important}
section[data-testid="stSidebar"] *{color:var(--ink)}
section[data-testid="stSidebar"] .aps-brand{color:var(--teal)}
/* text that must stay white on dark fills */
.stApp .aps-hero h1,.stApp .aps-hero p,.stApp .aps-hero span.aps-badge{color:#fff!important}.stApp .aps-hero span.aps-badge{color:#3b2a00!important}
.stApp .aps-table th{color:#fff!important}.stApp .aps-num,.stApp .aps-stat .ic{color:#fff!important}
.stApp .aps-chip.goal{color:#fff!important}.stApp .aps-chip.start{color:#3b2a00!important}
.stApp .aps-pill.p-ok{color:#0F6B47!important}.stApp .aps-pill.p-no{color:#9A2336!important}.stApp .aps-pill.p-rv{color:#8A5A07!important}.stApp .aps-pill.p-in{color:#0B4F5C!important}.stApp .aps-pill.p-mu{color:#4B5560!important}
.stApp .aps-card h4{color:var(--teal)!important}.stApp .aps-sub{color:var(--muted)!important}
.stApp .aps-note,.stApp .aps-note *{color:#4a3a10!important}.stApp .aps-note.info,.stApp .aps-note.info *{color:#0B3E47!important}
.stApp .aps-flow span.on{color:#fff!important}
</style>
"""

DECISION = {"Eligible": ("ok", "✅ Eligible"), "Not eligible": ("no", "❌ Not eligible"), "Needs review": ("rv", "❓ Needs review")}
CONF = {"High": "ok", "Medium": "rv", "Low": "no"}
REVIEW = {"auto": "p-ok", "check": "p-rv", "input": "p-in", "human": "p-no"}
TRI = {"TRUE": ("ok", "✅ Met"), "FALSE": ("no", "❌ Not met"), "UNKNOWN": ("rv", "❓ Unknown")}


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def show(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def hero(title: str, subtitle: str, badge: str = "Academic Pathway Finder") -> None:
    show(f"<div class='aps-hero'><span class='aps-badge'>{esc(badge)}</span><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>")


def flow(labels: list, active: str) -> None:
    show("<div class='aps-flow'>" + "".join(f"<span class='{'on' if l == active else ''}'>{esc(l)}</span>" for l in labels) + "</div>")


def pill(text, kind: str = "mu") -> Raw:
    return Raw(f"<span class='aps-pill p-{kind}'>{esc(text)}</span>")


def pill_raw(text, css: str) -> Raw:
    return Raw(f"<span class='aps-pill {css}'>{esc(text)}</span>")


def stats(items: list) -> None:
    """items: (number, label, css) triples."""
    icons = {"aps-ok": "✓", "aps-rv": "?", "aps-no": "✕", "aps-in": "◆"}
    show("<div class='aps-stats'>" + "".join(f"<div class='aps-stat {c}'><div class='ic'>{icons.get(c, '◆')}</div><div><b>{esc(n)}</b><span class='l'>{esc(l)}</span></div></div>" for n, l, c in items) + "</div>")


def ring(pct: float, kind: str) -> Raw:
    """Circular progress gauge: share of conditions met."""
    col = {"ok": "#1E9E6A", "rv": "#E9A23B", "no": "#D6455D"}.get(kind, "#13808F")
    return Raw(f"<div class='aps-ring' style='--p:{max(0, min(pct, 100)):.0f};--c:{col}'><b>{pct:.0f}%</b></div>")


def meter(passed: int, failed: int, unknown: int) -> Raw:
    t = max(passed + failed + unknown, 1)
    seg = lambda n, c: f"<i class='{c}' style='width:{100 * n / t:.1f}%'></i>" if n else ""
    return Raw(f"<div class='aps-meter'>{seg(passed, 'm-ok')}{seg(unknown, 'm-rv')}{seg(failed, 'm-no')}</div>")


def bar(value, required, state: str) -> Raw:
    """Marks bar: fill = your mark, tick = required mark. Non-numeric values give an empty cell."""
    try:
        v, r = float(str(value).rstrip("%")), float(str(required).rstrip("%"))
    except ValueError:
        return Raw("")
    colour = {"TRUE": "#10b981", "FALSE": "#ef4444"}.get(state, "#f59e0b")
    return Raw(f"<div class='aps-bar'><i style='width:{max(0, min(v, 100)):.1f}%;background:{colour}'></i><u style='left:{max(0, min(r, 100)):.1f}%'></u></div>")


def table(headers: list, rows: list) -> None:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>" for row in rows)
    show(f"<table class='aps-table'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")


def chain(chips: list) -> Raw:
    """chips: (text, css) pairs joined by arrows."""
    parts = []
    for i, (text, css) in enumerate(chips):
        parts.append(f"<span class='aps-chip {css}'>{esc(text)}</span>")
        if i < len(chips) - 1:
            parts.append("<span class='aps-arrow'>➜</span>")
    return Raw("<div class='aps-chain'>" + "".join(parts) + "</div>")


def note(text: str, info: bool = False) -> None:
    show(f"<div class='aps-note{' info' if info else ''}'>{esc(text)}</div>")
