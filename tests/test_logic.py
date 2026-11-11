import pytest
from engine.logic import Tri, compare, tri_and, tri_not, tri_or, to_number

T, F, U = Tri.TRUE, Tri.FALSE, Tri.UNKNOWN


@pytest.mark.parametrize("vals,exp", [([T, T], T), ([T, F], F), ([T, U], U), ([F, U], F), ([], T)])
def test_and_truth_table(vals, exp):
    assert tri_and(vals) is exp


@pytest.mark.parametrize("vals,exp", [([F, F], F), ([T, F], T), ([F, U], U), ([T, U], T), ([], F)])
def test_or_truth_table(vals, exp):
    assert tri_or(vals) is exp


def test_not():
    assert tri_not(T) is F and tri_not(F) is T and tri_not(U) is U


def test_compare_boundaries_and_unknown():
    assert compare(60, ">=", 60) is T
    assert compare(59.99, ">=", 60) is F
    assert compare(None, ">=", 60) is U


@pytest.mark.parametrize("bad", [None, "", "abc", -1, 101, float("nan"), True, "105"])
def test_to_number_rejects_invalid(bad):
    assert to_number(bad) is None


def test_to_number_accepts_percent_strings():
    assert to_number("55%") == 55.0 and to_number(" 72.5 ") == 72.5
