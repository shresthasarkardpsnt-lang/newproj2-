"""SQLite persistence: students, evaluations, decisions, missing conditions, certificates, roadmap, and an
editable versioned copy of the knowledge base (seeded from data/*.json)."""
from __future__ import annotations
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from engine.constants import DATA_DIR, ROOT
from engine.kb import KB_FILES, load_kb_from_json, validate_certificate, validate_programme, validate_route
from engine.validation import normalise_profile

DEFAULT_DB = ROOT / "database" / "academic_pathway.db"
KIND_KEY = {"programmes": "programmes", "certificates": "certificates", "routes": "routes"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS students(
  student_id TEXT PRIMARY KEY, name TEXT, profile_json TEXT NOT NULL, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS evaluation_runs(
  run_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL, run_at TEXT NOT NULL,
  preferred_programme TEXT, profile_json TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS eligibility_decisions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, programme_id TEXT, programme_name TEXT,
  decision TEXT, rule_version INTEGER, rule_expression TEXT, passed INTEGER, failed INTEGER, unknown INTEGER,
  final_explanation TEXT, FOREIGN KEY(run_id) REFERENCES evaluation_runs(run_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS missing_conditions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, programme_id TEXT, condition_label TEXT,
  result TEXT, student_value TEXT, required TEXT, gap REAL, explanation TEXT, missing_info TEXT,
  FOREIGN KEY(run_id) REFERENCES evaluation_runs(run_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS completed_certificates(
  student_id TEXT NOT NULL, cert_id TEXT NOT NULL, completed_on TEXT, PRIMARY KEY(student_id, cert_id));
CREATE TABLE IF NOT EXISTS roadmap_progress(
  student_id TEXT NOT NULL, target_id TEXT NOT NULL, item_key TEXT NOT NULL, done INTEGER NOT NULL,
  updated_at TEXT, PRIMARY KEY(student_id, target_id, item_key));
CREATE TABLE IF NOT EXISTS kb_items(
  kind TEXT NOT NULL, item_id TEXT NOT NULL, data_json TEXT NOT NULL, rule_version INTEGER NOT NULL DEFAULT 1,
  verification_status TEXT, verified_on TEXT, updated_at TEXT, PRIMARY KEY(kind, item_id));
CREATE TABLE IF NOT EXISTS kb_history(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, item_id TEXT, rule_version INTEGER, data_json TEXT,
  changed_at TEXT, change_note TEXT);
"""


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_db_path() -> Path:
    return Path(os.environ.get("APS_DB_PATH", DEFAULT_DB))


def connect(path: Optional[str] = None) -> sqlite3.Connection:
    path = str(path or get_db_path())
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection, data_dir: Optional[Path] = None) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
    if conn.execute("SELECT COUNT(*) FROM kb_items").fetchone()[0] == 0:
        seed_kb(conn, data_dir)


# ------------------------------------------------------------------- knowledge base
def _item_meta(kind: str, item: dict) -> tuple:
    src = item.get("source") if kind != "certificates" else item
    src = src or {}
    return src.get("verification_status"), src.get("verified_on")


def seed_kb(conn, data_dir: Optional[Path] = None) -> None:
    kb = load_kb_from_json(data_dir or DATA_DIR)
    for kind, items in kb.items():
        for it in items:
            _write_kb_item(conn, kind, it, note="Initial seed from data/*.json", bump=False)
    conn.commit()


def _write_kb_item(conn, kind, item, note="", bump=True) -> int:
    row = conn.execute("SELECT rule_version FROM kb_items WHERE kind=? AND item_id=?", (kind, item["id"])).fetchone()
    version = (row["rule_version"] + 1) if (row and bump) else (row["rule_version"] if row else int(item.get("rule_version", 1)))
    if kind in ("programmes", "routes"):
        item["rule_version"] = version
    status, verified_on = _item_meta(kind, item)
    blob = json.dumps(item, ensure_ascii=False)
    conn.execute("""INSERT INTO kb_items(kind,item_id,data_json,rule_version,verification_status,verified_on,updated_at)
                    VALUES(?,?,?,?,?,?,?) ON CONFLICT(kind,item_id) DO UPDATE SET data_json=excluded.data_json,
                    rule_version=excluded.rule_version, verification_status=excluded.verification_status,
                    verified_on=excluded.verified_on, updated_at=excluded.updated_at""",
                 (kind, item["id"], blob, version, status, verified_on, now()))
    conn.execute("INSERT INTO kb_history(kind,item_id,rule_version,data_json,changed_at,change_note) VALUES(?,?,?,?,?,?)",
                 (kind, item["id"], version, blob, now(), note))
    return version


def load_kb(conn) -> dict:
    kb = {}
    for kind in KB_FILES:
        rows = conn.execute("SELECT data_json FROM kb_items WHERE kind=? ORDER BY rowid", (kind,)).fetchall()
        kb[kind] = [json.loads(r["data_json"]) for r in rows]
    return kb


def upsert_kb_item(conn, kind: str, item: dict, note: str = "") -> tuple:
    """Validate then save. Returns (ok, errors_or_version). Rule version increments on every update."""
    kb = load_kb(conn)
    if kind == "programmes":
        errors = validate_programme(item)
    elif kind == "certificates":
        errors = validate_certificate(item)
    elif kind == "routes":
        errors = validate_route(item, kb)
    else:
        errors = [f"unknown kind {kind}"]
    if errors:
        return False, errors
    version = _write_kb_item(conn, kind, item, note=note or "Updated via administrator interface")
    conn.commit()
    return True, version


def delete_kb_item(conn, kind: str, item_id: str, note: str = "Deleted via administrator interface") -> bool:
    row = conn.execute("SELECT data_json, rule_version FROM kb_items WHERE kind=? AND item_id=?", (kind, item_id)).fetchone()
    if not row:
        return False
    conn.execute("INSERT INTO kb_history(kind,item_id,rule_version,data_json,changed_at,change_note) VALUES(?,?,?,?,?,?)",
                 (kind, item_id, row["rule_version"], row["data_json"], now(), note))
    conn.execute("DELETE FROM kb_items WHERE kind=? AND item_id=?", (kind, item_id))
    conn.commit()
    return True


def kb_history(conn, kind: Optional[str] = None, item_id: Optional[str] = None) -> list:
    q, args = "SELECT id,kind,item_id,rule_version,changed_at,change_note FROM kb_history WHERE 1=1", []
    if kind:
        q += " AND kind=?"; args.append(kind)
    if item_id:
        q += " AND item_id=?"; args.append(item_id)
    return [dict(r) for r in conn.execute(q + " ORDER BY id DESC", args).fetchall()]


def export_kb_to_json(conn, out_dir: Optional[Path] = None) -> list:
    out_dir = Path(out_dir or DATA_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    kb, written = load_kb(conn), []
    for kind, fname in KB_FILES.items():
        path = out_dir / fname
        path.write_text(json.dumps(kb[kind], indent=2, ensure_ascii=False), encoding="utf-8")
        written.append(str(path))
    return written


# ------------------------------------------------------------------- students
def save_student(conn, profile: dict) -> str:
    p = normalise_profile(profile)
    sid = str(p["student_id"]).strip()
    if not sid:
        raise ValueError("student_id is required")
    p["student_id"] = sid
    ts = now()
    conn.execute("""INSERT INTO students(student_id,name,profile_json,created_at,updated_at) VALUES(?,?,?,?,?)
                    ON CONFLICT(student_id) DO UPDATE SET name=excluded.name, profile_json=excluded.profile_json,
                    updated_at=excluded.updated_at""", (sid, p.get("name", ""), json.dumps(p), ts, ts))
    conn.commit()
    return sid


def get_student(conn, student_id: str) -> Optional[dict]:
    row = conn.execute("SELECT profile_json FROM students WHERE student_id=?", (student_id,)).fetchone()
    if not row:
        return None
    p = normalise_profile(json.loads(row["profile_json"]))
    p["certificates"] = list_completed_certificates(conn, student_id)  # source of truth is the table
    return p


def list_students(conn) -> list:
    return [dict(r) for r in conn.execute(
        "SELECT student_id,name,updated_at FROM students ORDER BY updated_at DESC").fetchall()]


def delete_student(conn, student_id: str) -> None:
    conn.execute("DELETE FROM evaluation_runs WHERE student_id=?", (student_id,))
    for t in ("completed_certificates", "roadmap_progress", "students"):
        conn.execute(f"DELETE FROM {t} WHERE student_id=?", (student_id,))
    conn.commit()


# ------------------------------------------------------------------- certificates & roadmap
def set_certificate_completed(conn, student_id: str, cert_id: str, completed: bool) -> None:
    if completed:
        conn.execute("INSERT OR IGNORE INTO completed_certificates(student_id,cert_id,completed_on) VALUES(?,?,?)",
                     (student_id, cert_id, now()[:10]))
    else:
        conn.execute("DELETE FROM completed_certificates WHERE student_id=? AND cert_id=?", (student_id, cert_id))
    conn.commit()


def sync_certificates(conn, student_id: str, cert_ids: list) -> None:
    current = set(list_completed_certificates(conn, student_id))
    for cid in set(cert_ids) - current:
        set_certificate_completed(conn, student_id, cid, True)
    for cid in current - set(cert_ids):
        set_certificate_completed(conn, student_id, cid, False)


def list_completed_certificates(conn, student_id: str) -> list:
    return [r["cert_id"] for r in conn.execute(
        "SELECT cert_id FROM completed_certificates WHERE student_id=? ORDER BY cert_id", (student_id,)).fetchall()]


def set_progress(conn, student_id: str, target_id: str, key: str, done: bool) -> None:
    conn.execute("""INSERT INTO roadmap_progress(student_id,target_id,item_key,done,updated_at) VALUES(?,?,?,?,?)
                    ON CONFLICT(student_id,target_id,item_key) DO UPDATE SET done=excluded.done, updated_at=excluded.updated_at""",
                 (student_id, target_id, key, int(done), now()))
    conn.commit()


def get_progress(conn, student_id: str, target_id: str) -> set:
    return {r["item_key"] for r in conn.execute(
        "SELECT item_key FROM roadmap_progress WHERE student_id=? AND target_id=? AND done=1", (student_id, target_id)).fetchall()}


# ------------------------------------------------------------------- evaluation history
def save_evaluation(conn, student_id: str, profile: dict, results: list, note: str = "") -> int:
    cur = conn.execute("INSERT INTO evaluation_runs(student_id,run_at,preferred_programme,profile_json,note) VALUES(?,?,?,?,?)",
                       (student_id, now(), profile.get("preferred_programme"), json.dumps(profile), note))
    run_id = cur.lastrowid
    for r in results:
        conn.execute("""INSERT INTO eligibility_decisions(run_id,programme_id,programme_name,decision,rule_version,
                        rule_expression,passed,failed,unknown,final_explanation) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                     (run_id, r.programme_id, r.programme_name, r.decision, r.rule_version, r.rule_expression,
                      len(r.passed), len(r.failed), len(r.unknown), r.final_explanation))
        for c in r.failed + r.unknown:
            conn.execute("""INSERT INTO missing_conditions(run_id,programme_id,condition_label,result,student_value,
                            required,gap,explanation,missing_info) VALUES(?,?,?,?,?,?,?,?,?)""",
                         (run_id, r.programme_id, c.label, c.result.value, c.student_value, c.required, c.gap,
                          c.explanation, c.missing_info))
    conn.commit()
    return run_id


def list_runs(conn, student_id: str) -> list:
    return [dict(r) for r in conn.execute("""
        SELECT r.run_id, r.run_at, r.preferred_programme, r.note,
          SUM(d.decision='Eligible') AS eligible, SUM(d.decision='Not eligible') AS not_eligible,
          SUM(d.decision='Needs review') AS needs_review
        FROM evaluation_runs r LEFT JOIN eligibility_decisions d ON d.run_id=r.run_id
        WHERE r.student_id=? GROUP BY r.run_id ORDER BY r.run_id DESC""", (student_id,)).fetchall()]


def run_decisions(conn, run_id: int) -> list:
    return [dict(r) for r in conn.execute("SELECT * FROM eligibility_decisions WHERE run_id=? ORDER BY id", (run_id,)).fetchall()]


def run_missing(conn, run_id: int) -> list:
    return [dict(r) for r in conn.execute("SELECT * FROM missing_conditions WHERE run_id=? ORDER BY id", (run_id,)).fetchall()]


def admin_stats(conn) -> dict:
    q = lambda sql: conn.execute(sql).fetchone()[0]
    return {"students": q("SELECT COUNT(*) FROM students"), "evaluation_runs": q("SELECT COUNT(*) FROM evaluation_runs"),
            "decisions": q("SELECT COUNT(*) FROM eligibility_decisions"),
            "completed_certificates": q("SELECT COUNT(*) FROM completed_certificates"),
            "programmes": q("SELECT COUNT(*) FROM kb_items WHERE kind='programmes'"),
            "certificates": q("SELECT COUNT(*) FROM kb_items WHERE kind='certificates'"),
            "routes": q("SELECT COUNT(*) FROM kb_items WHERE kind='routes'"),
            "unverified_items": q("SELECT COUNT(*) FROM kb_items WHERE verification_status IS NOT 'Verified'")}
