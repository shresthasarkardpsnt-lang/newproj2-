"""Three-valued (Kleene) predicate logic: TRUE / FALSE / UNKNOWN."""
from __future__ import annotations
import math
import operator
from enum import Enum
from typing import Iterable, Optional


class Tri(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


def tri_from_bool(value: Optional[bool]) -> Tri:
    if value is None:
        return Tri.UNKNOWN
    return Tri.TRUE if value else Tri.FALSE


def tri_and(values: Iterable[Tri]) -> Tri:
    """FALSE dominates; otherwise UNKNOWN dominates; empty conjunction is TRUE."""
    vals = list(values)
    if any(v is Tri.FALSE for v in vals):
        return Tri.FALSE
    if any(v is Tri.UNKNOWN for v in vals):
        return Tri.UNKNOWN
    return Tri.TRUE


def tri_or(values: Iterable[Tri]) -> Tri:
    """TRUE dominates; otherwise UNKNOWN dominates; empty disjunction is FALSE."""
    vals = list(values)
    if any(v is Tri.TRUE for v in vals):
        return Tri.TRUE
    if any(v is Tri.UNKNOWN for v in vals):
        return Tri.UNKNOWN
    return Tri.FALSE


def tri_not(value: Tri) -> Tri:
    if value is Tri.TRUE:
        return Tri.FALSE
    if value is Tri.FALSE:
        return Tri.TRUE
    return Tri.UNKNOWN


OPS = {">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt,
       "==": operator.eq, "!=": operator.ne}


def to_number(value, lo: float = 0.0, hi: float = 100.0) -> Optional[float]:
    """Return a float in [lo, hi] or None if missing / invalid / out of range."""
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, str):
            value = value.strip().rstrip("%")
            if value == "":
                return None
        num = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(num) or math.isinf(num) or num < lo or num > hi:
        return None
    return num


def compare(value: Optional[float], op: str, threshold: float) -> Tri:
    """Predicate `value op threshold`; UNKNOWN when the value is missing."""
    if value is None:
        return Tri.UNKNOWN
    return tri_from_bool(OPS[op](round(float(value), 6), round(float(threshold), 6)))


def member_of(value, allowed) -> Tri:
    if value is None or value == "":
        return Tri.UNKNOWN
    return tri_from_bool(str(value).strip().lower() in {str(a).strip().lower() for a in allowed})


def fmt(x) -> str:
    """Compact number formatting: 58.0 -> '58', 57.5 -> '57.5'."""
    if x is None:
        return "-"
    return f"{float(x):g}"
