# Academic Pathway Reasoning & Improvement System

A local Streamlit application that evaluates a student's academic eligibility for programmes, explains exactly why
they do or do not qualify, and suggests realistic ways to improve preparation or use alternative routes.

* **Deterministic rule-based reasoning**: three-valued predicate logic (TRUE / FALSE / UNKNOWN). No scores, no
  probabilities, no learned models.
* **No chatbot, no AI counsellor, no external LLM or network calls.** Works fully offline. (Verified by an automated test.)
* **Sample data is illustrative.** Every programme, route and certificate in `data/` is a *sample* and labelled
  "Illustrative sample" / "Unverified". Nothing is presented as an official university requirement.

## Install, run, test

```bash
pip install -r requirements.txt     # Python 3.10+ recommended
streamlit run app.py                # streamlined 3-page evaluation  (http://localhost:8501)
streamlit run app_full.py           # full 14-page version (all features below)
pytest -q                           # 82 tests
```

### Which app should I use?
* **`app.py` (default, redesigned):** a five-step applicant interface: *Profile*, *Programmes*, *Gaps & pathways*, *Reasoning*,
  *Quality & KB*. Shows eligible programmes, missing conditions, alternative pathways, the reasoning chain behind every
  conclusion, a confidence label, supporting evidence, exception handling and human-review states, plus a baseline
  comparison, documented test cases and measured metrics. Interactive: filters, search, expandable reasoning, review
  check-boxes, what-if sliders, live evaluation run. Same engine and rules as the full version (logic in `engine/applicant.py`).
* **`app_full.py` (full):** the original 14-page version with every feature below.

Works from VS Code: open the folder, select a Python interpreter, run the commands above in the integrated terminal.
The SQLite database (`database/academic_pathway.db`) is created automatically on first run and seeded from `data/*.json`.
Click **Load a demo student** on the Dashboard for a ready-made sample (overall 58, Maths 45, Physics 65).

Optional: set `APS_ADMIN_PASSWORD` to protect the Administrator page; set `APS_DB_PATH` to use another database file.

## Pages (full version, `app_full.py`)

| # | Page | What it does |
|---|---|---|
| 1 | Dashboard | Decision counts, preferred-programme summary, roadmap progress |
| 2 | Student Profile | Create / edit / validate a profile; missing data allowed |
| 3 | Eligibility Evaluation | All programmes, filters, full explanation per rule, CSV/PDF, save to history |
| 4 | Missing Conditions Analyzer | Passed / failed / unknown conditions, exact numeric gaps, next steps |
| 5 | Higher Eligibility Opportunities | Stricter programmes, threshold comparison, gaps; "higher ≠ better" notice |
| 6 | Alternative Academic Pathways | Routes with prerequisite checks, NetworkX pathway graphs, sources |
| 7 | Certificate Recommendation Planner | Four categories, reasons, URLs, recognition and evidence |
| 8 | Certificate Impact Analysis | Formal-eligibility vs preparation vs profile effects, before/after check |
| 9 | What-if Simulator | Hypothetical marks/stream/entrance; real profile never modified |
| 10 | Academic Improvement Roadmap | Seven-stage checklist with persistent progress and re-evaluation |
| 11 | Programme Knowledge Base | Browse programmes, requirements, routes, progression graph |
| 12 | Evaluation History | Saved runs, stored missing conditions, run-to-run comparison |
| 13 | Administrator Dashboard | Add/update programmes, certificates, routes, sources; rule versions; JSON export |
| 14 | Testing & Performance | Live metrics vs baseline; run pytest from the UI |

## Architecture

```
app.py / app_full.py    streamlined 3-page app / full 14-page app
data/                   programmes.json, certificates.json, alternative_routes.json  (seed data)
engine/
  logic.py              Tri enum, Kleene AND/OR/NOT, safe numeric parsing, comparisons
  eligibility.py        requirement predicates -> ConditionResult / EvaluationResult
  explain.py            8-part explanations + completeness check
  missing.py            marks-gap table, information required, next steps
  higher.py             higher-threshold analysis
  pathway.py            route evaluation + NetworkX graphs
  certificates.py       recommendations + impact analysis
  simulator.py          what-if on a deep copy
  roadmap.py            seven-stage roadmap
  evaluation.py         seeded synthetic data, independent reference, if/else baseline, metrics
  kb.py / validation.py knowledge-base schema validation; profile validation
  reports.py            CSV / PDF (reportlab)
database/db.py          SQLite: students, runs, decisions, missing conditions, certificates, roadmap, versioned KB
ui/                     one module per page (lite_*.py = streamlined app)
tests/                  pytest suite (82 tests, including headless UI tests)
reports/                generated reports are saved here when requested
```

**How a decision is made.** A programme is a conjunction of requirement predicates (`min_overall`, `min_class10`,
`min_subject`, `subject_studied`, `stream_in`, `entrance`, `qualification`, `certificate`, and `any_of` for OR-groups).
Each predicate yields TRUE/FALSE/UNKNOWN using Kleene logic: any FALSE → **Not eligible**; otherwise any UNKNOWN →
**Needs review**; otherwise **Eligible**. Missing or out-of-range inputs become UNKNOWN, never a guess.
Example: `Overall >= 65 AND Mathematics >= 60 AND Physics >= 45 AND Entrance(JEE Main) == Qualified`.

**Certificates.** A certificate can only affect eligibility when a programme rule explicitly names it
(type `certificate`). In the sample data only one does (a bridge course in the illustrative MCA rule). All other
certificates affect preparation/profile only, which the Impact Analysis page demonstrates and tests enforce.

**Editing the knowledge base.** The administrator edits the SQLite copy; each save validates the item, bumps the rule
version and records history. "Verified" is rejected unless an official URL and verification date are supplied. Use
*Export* to write changes back to `data/*.json`.

## Test results (measured, reproducible)

`pytest -q` → **82 passed** (clean virtualenv, Python 3.12). Covers normal eligibility, boundary marks, missing
information, invalid marks, failed prerequisites, alternative routes, certificate recognition, what-if scenarios,
database operations, explanation completeness, data integrity, absence of chatbot/LLM code, and headless UI flows.

Evaluation suite (300 seeded synthetic profiles × 14 programmes, seed 42; Testing & Performance page):

| System (complete profiles, 4,200 decisions) | Accuracy | Precision | Recall | F1 | TP/FP/FN/TN |
|---|---|---|---|---|---|
| Rule engine | 1.000 | 1.000 | 1.000 | 1.000 | 1113/0/0/3087 |
| Simple if/else baseline | 0.790 | 0.558 | 1.000 | 0.716 | 1113/882/0/2205 |

* Incomplete profiles (25% of fields blanked): engine gave a definite answer for 79.1% of cases with **0 wrong definite
  answers** and 0 false "Eligible"; the other 20.9% became "Needs review". The baseline (missing treated as 0) was
  correct 73.9% of the time and produced 874 false "Eligible" outcomes.
* Rule coverage: 46/46 rules exercised, 46/46 seen as both TRUE and FALSE.
* Explanation completeness: 100% (8,400 decisions checked field-by-field).
* Speed: about 0.055 ms per programme, 0.77 ms per student across all 14 programmes (machine-dependent).

## Known limitations (please read)

* **The engine's 1.000 does not prove real-world correctness.** The "ground truth" is an independent reference
  implementation of the *same sample rules*, so the test shows the engine implements them faithfully, nothing more.
  The baseline comparison shows what simple if/else logic misses (entrance exams, qualifications, OR-rules, missing data).
* Programme thresholds, routes and progression links are **illustrative samples, not official requirements**. Certificate
  entries name real issuers and give issuer home-page URLs only; course pages, durations and costs are shown as
  "Not verified". Before real use, verify against official sources and mark items Verified in the admin page.
* Entrance results marked "Registered" or "Appeared - result awaited" are UNKNOWN by design.
* Eligibility is evaluated per programme against structured fields; real admissions can include seat quotas,
  category reservations, age limits, interviews or portfolios that are not modelled.
* Match strength for certificates ("High/Medium/Low") counts matching factors; it is not a probability.
* The administrator password is a simple optional environment-variable gate for local use, not production security.
* Streamlit currently emits a pandas deprecation warning from its own chart code during tests; it is harmless.
* Not tested in a real desktop browser by a human; page rendering and interactions were verified with Streamlit's headless
  `AppTest` and a live server health/HTTP check.
