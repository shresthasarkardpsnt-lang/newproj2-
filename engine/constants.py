"""Shared constants for the reasoning engine and the UI."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"

ELIGIBLE = "Eligible"
NOT_ELIGIBLE = "Not eligible"
NEEDS_REVIEW = "Needs review"
DECISIONS = [ELIGIBLE, NOT_ELIGIBLE, NEEDS_REVIEW]

STREAMS = ["Science (PCM)", "Science (PCB)", "Science (PCMB)", "Commerce",
           "Arts / Humanities", "Vocational", "Other"]
CORE_SUBJECTS = ["mathematics", "physics", "chemistry", "biology", "computer_science", "english"]
SUBJECT_LABELS = {"mathematics": "Mathematics", "physics": "Physics", "chemistry": "Chemistry",
                  "biology": "Biology", "computer_science": "Computer Science", "english": "English"}

BASE_ENTRANCE_EXAMS = ["JEE Main", "State CET", "NIMCET", "CUET-PG", "State PGCET"]
ENTRANCE_NOT_SPECIFIED = "Not specified"
ENTRANCE_STATUSES = [ENTRANCE_NOT_SPECIFIED, "Not taken", "Registered / appearing",
                     "Appeared - result awaited", "Qualified"]
ENTRANCE_PENDING = ("Registered / appearing", "Appeared - result awaited")

DISCIPLINES = ["Computer Science", "Computer Applications", "Information Technology", "Engineering",
               "Mathematics", "Statistics", "Science", "Commerce", "Arts / Humanities", "Other"]
DIPLOMA_BRANCHES = ["Computer Engineering", "Information Technology", "Electronics & Communication",
                    "Mechanical", "Civil", "Other"]

LEVELS = ["Foundation", "Diploma", "UG", "PG"]
FIELDS = ["Computer Science", "AI/ML", "Information Technology", "Electronics", "Data Science", "Cybersecurity"]
VERIFICATION_STATUSES = ["Illustrative sample", "Unverified", "Verified"]
RECOGNISED_VALUES = ["Verified - recognised", "Unverified", "Not recognised"]
REQ_TYPES = ["min_overall", "min_class10", "min_subject", "subject_studied", "stream_in",
             "entrance", "qualification", "certificate", "any_of"]

CERT_CATEGORIES = ["Admission requirement certificates", "Academic preparation courses",
                   "Professional skill certificates", "Profile-strengthening certificates"]

CAREER_INTERESTS = ["Software development", "Artificial intelligence", "Data analysis", "Cybersecurity",
                    "Electronics & hardware", "Networking & cloud", "Research & academia"]
# Knowledge areas a field needs (used for deterministic certificate matching).
FIELD_AREAS = {
    "Computer Science": ["programming", "mathematics"],
    "AI/ML": ["programming", "mathematics", "statistics", "machine_learning"],
    "Information Technology": ["programming", "databases", "networking"],
    "Electronics": ["mathematics", "physics", "electronics"],
    "Data Science": ["statistics", "programming", "databases"],
    "Cybersecurity": ["networking", "security", "programming"],
}
INTEREST_AREAS = {
    "Software development": ["programming"],
    "Artificial intelligence": ["machine_learning", "mathematics"],
    "Data analysis": ["statistics", "databases"],
    "Cybersecurity": ["security", "networking"],
    "Electronics & hardware": ["electronics", "physics"],
    "Networking & cloud": ["networking"],
    "Research & academia": ["mathematics"],
}
SUBJECT_AREA = {"mathematics": "mathematics", "physics": "physics", "computer_science": "programming",
                "chemistry": "chemistry", "biology": "biology", "english": "english"}
TECHNICAL_FIELDS = set(FIELD_AREAS)
