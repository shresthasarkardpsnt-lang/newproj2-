import copy
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("APS_DB_PATH", str(Path(tempfile.mkdtemp()) / "test_app.db"))

import pytest  # noqa: E402

from database import db  # noqa: E402
from engine.kb import load_kb_from_json  # noqa: E402


@pytest.fixture(scope="session")
def kb():
    return load_kb_from_json()


@pytest.fixture()
def conn():
    c = db.connect(":memory:")
    yield c
    c.close()


def make_profile(**over):
    """Hand-built profile helper. Defaults describe a strong PCM student who qualified JEE Main."""
    p = {"student_id": "T1", "name": "Test", "class10_pct": 80, "class12_pct": 75, "stream": "Science (PCM)",
         "overall_pct": 75, "marks": {"mathematics": 70, "physics": 65, "chemistry": 60, "english": 60},
         "entrance_exams": {"JEE Main": {"status": "Qualified", "score": 90}},
         "diploma": {"has": False}, "bachelor": {"has": False}, "certificates": []}
    for k, v in over.items():
        if k == "marks":
            p["marks"] = {**p["marks"], **v}
        else:
            p[k] = v
    return copy.deepcopy(p)


@pytest.fixture()
def strong():
    return make_profile()


@pytest.fixture()
def weak():
    """The brief's example: overall 58, maths 45, physics 65."""
    return make_profile(overall_pct=58, marks={"mathematics": 45, "physics": 65},
                        entrance_exams={"JEE Main": {"status": "Not taken"}})
