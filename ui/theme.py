```python
"""Look and feel: one stylesheet plus tiny HTML helpers.

Every dynamic string goes through `esc`, so student names or rule text
can never inject markup.
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
/* =========================================================
   COLOUR VARIABLES
   ========================================================= */
:root {
    --ink: #1B2B34;
    --muted: #5B6B73;
    --teal: #0B4F5C;
    --teal2: #13808F;
    --coral: #E2552F;
    --gold: #F4B942;
    --cream: #F6F1E9;
    --mint: #E4EFEC;

    --ok: #1E9E6A;
    --rv: #E9A23B;
    --no: #D6455D;

    --line: rgba(11, 79, 92, .16);
    --shadow: 0 6px 18px rgba(11, 79, 92, .10);

    /* Form colours */
    --input-bg: #292622;
    --input-text: #FFFFFF;
    --input-placeholder: #B8B8B8;
    --input-border: #55514B;
}


/* =========================================================
   MAIN APP
   ========================================================= */
:root, html, body, .stApp {
    color-scheme: light !important;
}

.stApp {
    background: var(--cream);
    color: var(--ink);
}

.block-container {
    max-width: 1120px;
    padding-top: 1.2rem;
    padding-bottom: 4rem;
}


/* =========================================================
   TYPOGRAPHY
   ========================================================= */
h1, h2, h3,
.aps-hero h1,
.aps-card h4,
.aps-brand {
    font-family: Georgia, 'Times New Roman', serif !important;
    letter-spacing: -.01em;
}

h1, h2, h3 {
    color: var(--teal) !important;
}


/* =========================================================
   SIDEBAR
   ========================================================= */
section[data-testid="stSidebar"] {
    background: var(--mint);
    border-right: 1px solid var(--line);
}

section[data-testid="stSidebar"] * {
    color: var(--ink);
}

.aps-brand {
    font-size: 1.45rem;
    font-weight: 700;
    color: var(--teal);
    margin: 0 0 2px 0;
}

.aps-brandsub {
    font-size: .82rem;
    color: var(--muted);
    margin-bottom: 12px;
}


/* =========================================================
   HERO SECTION
   ========================================================= */
.aps-hero {
    position: relative;
    overflow: hidden;
    background: linear-gradient(
        135deg,
        #0B4F5C 0%,
        #13808F 70%,
        #2BB1A6 120%
    );
    color: #fff;
    border-radius: 24px;
    padding: 30px 34px;
    margin-bottom: 16px;
    box-shadow: var(--shadow);
}

.aps-hero:before {
    content: "";
    position: absolute;
    right: -60px;
    top: -70px;
    width: 240px;
    height: 240px;
    border-radius: 50%;
    background: radial-gradient(
        circle,
        rgba(244, 185, 66, .55),
        rgba(244, 185, 66, 0) 70%
    );
}

.aps-hero:after {
    content: "";
    position: absolute;
    right: 120px;
    bottom: -90px;
    width: 200px;
    height: 200px;
    border-radius: 50%;
    background: radial-gradient(
        circle,
        rgba(226, 85, 47, .45),
        rgba(226, 85, 47, 0) 70%
    );
}

.aps-hero h1 {
    position: relative;
    margin: 0 0 6px 0;
    font-size: 2rem;
    color: #fff !important;
    padding: 0;
}

.aps-hero p {
    position: relative;
    margin: 0;
    opacity: .92;
    font-size: 1rem;
    max-width: 720px;
    color: #fff !important;
}

.aps-badge {
    position: relative;
    display: inline-block;
    background: var(--gold);
    color: #3b2a00 !important;
    font-weight: 700;
    font-size: .72rem;
    letter-spacing: .08em;
    text-transform: uppercase;
    border-radius: 99px;
    padding: 3px 12px;
    margin-bottom: 10px;
}


/* =========================================================
   STATISTICS
   ========================================================= */
.aps-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 14px;
    margin: 10px 0 18px;
}

.aps-stat {
    display: flex;
    align-items: center;
    gap: 14px;
    background: #fff;
    border-radius: 18px;
    padding: 14px 16px;
    border: 1px solid var(--line);
    box-shadow: var(--shadow);
}

.aps-stat .ic {
    flex: 0 0 42px;
    height: 42px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    color: #fff !important;
    font-weight: 700;
}

.aps-stat b {
    display: block;
    font-family: Georgia, serif;
    font-size: 1.9rem;
    line-height: 1;
    color: var(--ink);
}

.aps-stat span.l {
    font-size: .82rem;
    color: var(--muted);
}

.aps-ok .ic { background: var(--ok); }
.aps-rv .ic { background: var(--rv); }
.aps-no .ic { background: var(--no); }
.aps-in .ic { background: var(--teal2); }


/* =========================================================
   CARDS
   ========================================================= */
.aps-card {
    display: flex;
    gap: 18px;
    align-items: center;
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 16px 20px;
    margin: 12px 0 4px;
    box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
}

.aps-card:before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 6px;
}

.aps-card.ok:before { background: var(--ok); }
.aps-card.no:before { background: var(--no); }
.aps-card.rv:before { background: var(--rv); }

.aps-body {
    flex: 1;
    min-width: 0;
}

.aps-card h4 {
    margin: 0 0 2px 0;
    font-size: 1.15rem;
    color: var(--teal) !important;
}

.aps-sub {
    font-size: .84rem;
    color: var(--muted) !important;
    margin-bottom: 6px;
}


/* =========================================================
   PROGRESS RING AND METERS
   ========================================================= */
.aps-ring {
    flex: 0 0 74px;
    height: 74px;
    border-radius: 50%;
    background: conic-gradient(
        var(--c) calc(var(--p) * 1%),
        rgba(11, 79, 92, .12) 0
    );
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}

.aps-ring:before {
    content: "";
    position: absolute;
    inset: 8px;
    border-radius: 50%;
    background: #fff;
}

.aps-ring b {
    position: relative;
    font-family: Georgia, serif;
    font-size: 1.05rem;
    color: var(--ink);
}

.aps-meter {
    height: 8px;
    border-radius: 99px;
    background: rgba(11, 79, 92, .12);
    overflow: hidden;
    margin: 8px 0 2px;
    display: flex;
}

.aps-meter i {
    display: block;
    height: 100%;
}

.m-ok { background: var(--ok); }
.m-no { background: var(--no); }
.m-rv { background: var(--rv); }


/* =========================================================
   PILLS
   ========================================================= */
.aps-pill {
    display: inline-block;
    border-radius: 999px;
    padding: 3px 12px;
    font-size: .76rem;
    font-weight: 700;
    margin: 2px 6px 2px 0;
    border: 1px solid transparent;
}

.p-ok { background: #DDF3EA; color: #0F6B47 !important; }
.p-no { background: #FBE1E5; color: #9A2336 !important; }
.p-rv { background: #FCEBCB; color: #8A5A07 !important; }
.p-in { background: #D9EEF1; color: #0B4F5C !important; }
.p-mu { background: #ECE7DE; color: #4B5560 !important; }


/* =========================================================
   TABLES
   ========================================================= */
.aps-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: .9rem;
    margin: 8px 0 14px;
    background: #fff;
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid var(--line);
    box-shadow: var(--shadow);
}

.aps-table th {
    text-align: left;
    padding: 11px 14px;
    background: var(--teal);
    color: #fff !important;
    font-weight: 600;
    font-size: .82rem;
    letter-spacing: .03em;
}

.aps-table td {
    padding: 10px 14px;
    border-bottom: 1px solid rgba(11, 79, 92, .10);
    vertical-align: top;
}

.aps-table tr:nth-child(even) td {
    background: #FAF7F1;
}

.aps-table tr:last-child td {
    border-bottom: none;
}


/* =========================================================
   INPUT FIELDS - IMPORTANT FIX
   ========================================================= */

/* Dark background for all text and number inputs */
div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-baseweb="textarea"],
textarea {
    background-color: var(--input-bg) !important;
    border: 1px solid var(--input-border) !important;
    border-radius: 12px !important;
}


/* Dropdown main box */
div[data-baseweb="select"] > div {
    background-color: var(--input-bg) !important;
    border: 1px solid var(--input-border) !important;
    border-radius: 12px !important;
}


/* User typed text - WHITE */
input,
textarea {
    color: var(--input-text) !important;
    -webkit-text-fill-color: var(--input-text) !important;
    caret-color: #FFFFFF !important;
}


/* Text inside Streamlit select boxes */
div[data-baseweb="select"] {
    color: var(--input-text) !important;
}

div[data-baseweb="select"] span,
div[data-baseweb="select"] input,
div[data-baseweb="select"] div {
    color: var(--input-text) !important;
    -webkit-text-fill-color: var(--input-text) !important;
}


/* Placeholder text */
input::placeholder,
textarea::placeholder {
    color: var(--input-placeholder) !important;
    -webkit-text-fill-color: var(--input-placeholder) !important;
    opacity: 1 !important;
}


/* Focus effect */
div[data-baseweb="input"]:focus-within,
div[data-baseweb="base-input"]:focus-within,
div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="textarea"]:focus-within {
    border-color: var(--coral) !important;
    box-shadow: 0 0 0 2px rgba(226, 85, 47, .25) !important;
}


/* Dropdown arrow */
div[data-baseweb="select"] svg,
div[data-baseweb="input"] svg {
    fill: #FFFFFF !important;
}


/* Number input buttons */
div[data-testid="stNumberInput"] button {
    background: var(--input-bg) !important;
    color: #FFFFFF !important;
}


/* =========================================================
   DROPDOWN MENU OPTIONS
   ========================================================= */

/* Keep the opened dropdown menu light and readable */
div[data-baseweb="popover"],
div[data-baseweb="popover"] ul,
div[data-baseweb="menu"],
ul[role="listbox"] {
    background: #FFFFFF !important;
}

/* Dropdown option text */
div[data-baseweb="popover"] li,
div[data-baseweb="popover"] li *,
ul[role="listbox"] li,
ul[role="listbox"] li * {
    background: #FFFFFF !important;
    color: var(--ink) !important;
    -webkit-text-fill-color: var(--ink) !important;
}

/* Selected and hovered options */
ul[role="listbox"] li:hover,
ul[role="listbox"] li[aria-selected="true"] {
    background: var(--mint) !important;
}


/* =========================================================
   FORM CONTAINER
   ========================================================= */
div[data-testid="stForm"] {
    background: #FFFFFF;
    border: 1px solid var(--line) !important;
    border-radius: 20px;
    box-shadow: var(--shadow);
    padding: 6px 10px;
}


/* =========================================================
   FORM LABELS
   ========================================================= */
.stApp [data-testid="stWidgetLabel"] p,
.stApp label,
.stApp [data-testid="stWidgetLabel"] * {
    color: var(--teal) !important;
}

.stApp [data-testid="stWidgetLabel"] p {
    font-weight: 600;
}


/* =========================================================
   BUTTONS
   ========================================================= */
.stButton > button,
.stDownloadButton > button,
div[data-testid="stFormSubmitButton"] > button {
    border-radius: 999px;
    font-weight: 700;
    padding: .45rem 1.4rem;
    border: 1px solid var(--teal);
    transition: all .15s ease;
}

.stButton > button,
.stDownloadButton > button {
    background: #FFFFFF !important;
    color: var(--teal) !important;
    -webkit-text-fill-color: var(--teal);
}

.stButton > button p,
.stDownloadButton > button p {
    color: inherit !important;
}

.stButton > button[kind="primary"],
div[data-testid="stFormSubmitButton"] > button {
    background: var(--coral) !important;
    border-color: var(--coral) !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF;
}

.stButton > button[kind="primary"] p,
div[data-testid="stFormSubmitButton"] > button p {
    background: transparent !important;
    color: #FFFFFF !important;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow);
}


/* =========================================================
   RADIO BUTTONS
   ========================================================= */
div[data-testid="stRadio"] [role="radiogroup"] {
    gap: 8px;
    flex-wrap: wrap;
}

div[data-testid="stRadio"] label[data-baseweb="radio"] {
    background: #FFFFFF;
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 6px 16px;
    margin: 0;
    transition: all .15s ease;
    box-shadow: 0 2px 6px rgba(11, 79, 92, .06);
}

div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
    display: none;
}

div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
    border-color: var(--teal2);
    transform: translateY(-1px);
}

div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
    background: var(--teal);
    border-color: var(--teal);
}

div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) * {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    font-weight: 700;
}


/* =========================================================
   TABS, EXPANDERS AND ALERTS
   ========================================================= */
button[data-baseweb="tab"] {
    font-weight: 600;
    border-radius: 12px 12px 0 0;
}

button[data-baseweb="tab"] p {
    color: var(--ink) !important;
}

button[data-baseweb="tab"][aria-selected="true"] p {
    color: var(--coral) !important;
    font-weight: 700;
}

div[data-baseweb="tab-highlight"] {
    background: var(--coral) !important;
    height: 3px !important;
}

div[data-testid="stExpander"] {
    background: #FFFFFF;
    border: 1px solid var(--line) !important;
    border-radius: 16px !important;
    box-shadow: 0 2px 8px rgba(11, 79, 92, .06);
    margin-bottom: 6px;
}

div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] summary * {
    color: var(--teal) !important;
}

div[data-testid="stExpander"] details {
    background: #FFFFFF;
}

div[data-testid="stAlert"] {
    border-radius: 14px;
}

div[data-testid="stAlert"],
div[data-testid="stAlert"] * {
    color: var(--ink) !important;
}

hr {
    border-color: var(--line) !important;
}


/* =========================================================
   SLIDERS AND CHECKBOXES
   ========================================================= */
div[data-testid="stCheckbox"] label *,
div[data-testid="stSlider"] * {
    color: var(--ink);
}

div[data-testid="stSlider"] [data-testid="stThumbValue"] {
    color: var(--coral) !important;
    font-weight: 700;
}


/* =========================================================
   CUSTOM COMPONENTS
   ========================================================= */
.aps-chain {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin: 10px 0;
}

.aps-chip {
    border-radius: 999px;
    padding: 7px 15px;
    font-size: .84rem;
    background: #FFFFFF;
    border: 1px solid var(--line);
    box-shadow: 0 2px 6px rgba(11, 79, 92, .08);
}

.aps-chip.start {
    background: var(--gold);
    border-color: var(--gold);
    color: #3b2a00 !important;
    font-weight: 700;
}

.aps-chip.goal {
    background: var(--teal);
    color: #FFFFFF !important;
    border-color: var(--teal);
    font-weight: 700;
}

.aps-arrow {
    color: var(--coral);
    font-weight: 700;
}

.aps-note {
    border-radius: 16px;
    padding: 12px 16px;
    background: #FFF4DA;
    border: 1px solid #F1D48A;
    border-left: 6px solid var(--gold);
    font-size: .9rem;
    margin: 10px 0;
    color: #4a3a10 !important;
}

.aps-note.info {
    background: #E3F3F4;
    border-color: #A9D6DA;
    border-left-color: var(--teal2);
    color: #0B3E47 !important;
}

.aps-flow {
    display: flex;
    gap: 8px;
    margin: 2px 0 10px;
    flex-wrap: wrap;
}

.aps-flow span {
    flex: 1;
    min-width: 120px;
    text-align: center;
    padding: 7px 4px;
    border-radius: 999px;
    font-size: .82rem;
    background: #FFFFFF;
    border: 1px solid var(--line);
    color: var(--muted);
}

.aps-flow span.on {
    background: var(--teal);
    color: #FFFFFF !important;
    font-weight: 700;
}

</style>
"""


# =========================================================
# STATUS CONSTANTS
# =========================================================
DECISION = {
    "Eligible": ("ok", "✅ Eligible"),
    "Not eligible": ("no", "❌ Not eligible"),
    "Needs review": ("rv", "❓ Needs review"),
}

CONF = {
    "High": "ok",
    "Medium": "rv",
    "Low": "no",
}

REVIEW = {
    "auto": "p-ok",
    "check": "p-rv",
    "input": "p-in",
    "human": "p-no",
}

TRI = {
    "TRUE": ("ok", "✅ Met"),
    "FALSE": ("no", "❌ Not met"),
    "UNKNOWN": ("rv", "❓ Unknown"),
}


# =========================================================
# HELPER FUNCTIONS
# =========================================================
def inject() -> None:
    """Inject the application's CSS."""
    st.markdown(CSS, unsafe_allow_html=True)


def show(markup: str) -> None:
    """Display safe HTML markup."""
    st.markdown(markup, unsafe_allow_html=True)


def hero(
    title: str,
    subtitle: str,
    badge: str = "Academic Pathway Finder"
) -> None:
    show(
        f"<div class='aps-hero'>"
        f"<span class='aps-badge'>{esc(badge)}</span>"
        f"<h1>{esc(title)}</h1>"
        f"<p>{esc(subtitle)}</p>"
        f"</div>"
    )


def flow(labels: list, active: str) -> None:
    content = "".join(
        f"<span class='{'on' if label == active else ''}'>"
        f"{esc(label)}</span>"
        for label in labels
    )
    show("<div class='aps-flow'>" + content + "</div>")


def pill(text, kind: str = "mu") -> Raw:
    return Raw(
        f"<span class='aps-pill p-{kind}'>{esc(text)}</span>"
    )


def pill_raw(text, css: str) -> Raw:
    return Raw(
        f"<span class='aps-pill {css}'>{esc(text)}</span>"
    )


def stats(items: list) -> None:
    """items: (number, label, css) triples."""
    icons = {
        "aps-ok": "✓",
        "aps-rv": "?",
        "aps-no": "✕",
        "aps-in": "◆",
    }

    content = "".join(
        f"<div class='aps-stat {css}'>"
        f"<div class='ic'>{icons.get(css, '◆')}</div>"
        f"<div><b>{esc(number)}</b>"
        f"<span class='l'>{esc(label)}</span></div>"
        f"</div>"
        for number, label, css in items
    )

    show("<div class='aps-stats'>" + content + "</div>")


def ring(pct: float, kind: str) -> Raw:
    """Circular progress gauge: share of conditions met."""
    colour = {
        "ok": "#1E9E6A",
        "rv": "#E9A23B",
        "no": "#D6455D",
    }.get(kind, "#13808F")

    percentage = max(0, min(pct, 100))

    return Raw(
        f"<div class='aps-ring' "
        f"style='--p:{percentage:.0f};--c:{colour}'>"
        f"<b>{pct:.0f}%</b></div>"
    )


def meter(passed: int, failed: int, unknown: int) -> Raw:
    total = max(passed + failed + unknown, 1)

    def segment(number, css):
        if not number:
            return ""
        width = 100 * number / total
        return f"<i class='{css}' style='width:{width:.1f}%'></i>"

    return Raw(
        "<div class='aps-meter'>"
        + segment(passed, "m-ok")
        + segment(unknown, "m-rv")
        + segment(failed, "m-no")
        + "</div>"
    )


def bar(value, required, state: str) -> Raw:
    """Marks bar: fill = your mark, tick = required mark."""
    try:
        value_number = float(str(value).rstrip("%"))
        required_number = float(str(required).rstrip("%"))
    except ValueError:
        return Raw("")

    colour = {
        "TRUE": "#10b981",
        "FALSE": "#ef4444",
    }.get(state, "#f59e0b")

    value_number = max(0, min(value_number, 100))
    required_number = max(0, min(required_number, 100))

    return Raw(
        f"<div class='aps-bar'>"
        f"<i style='width:{value_number:.1f}%;"
        f"background:{colour}'></i>"
        f"<u style='left:{required_number:.1f}%'></u>"
        f"</div>"
    )


def table(headers: list, rows: list) -> None:
    head = "".join(
        f"<th>{esc(header)}</th>"
        for header in headers
    )

    body = "".join(
        "<tr>"
        + "".join(f"<td>{esc(cell)}</td>" for cell in row)
        + "</tr>"
        for row in rows
    )

    show(
        f"<table class='aps-table'>"
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody>"
        f"</table>"
    )


def chain(chips: list) -> Raw:
    """chips: (text, css) pairs joined by arrows."""
    parts = []

    for index, (text, css) in enumerate(chips):
        parts.append(
            f"<span class='aps-chip {css}'>{esc(text)}</span>"
        )

        if index < len(chips) - 1:
            parts.append("<span class='aps-arrow'>➜</span>")

    return Raw(
        "<div class='aps-chain'>"
        + "".join(parts)
        + "</div>"
    )


def note(text: str, info: bool = False) -> None:
    show(
        f"<div class='aps-note{' info' if info else ''}'>"
        f"{esc(text)}</div>"
    )
```
