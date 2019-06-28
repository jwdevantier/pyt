import pytest
from pyt.utils import spec as s


def expected_msg(exp, act):
    return f"expected '{exp}', got '{act}'"


class SometType:
    def __str__(self):
        return "SomeType"


################################################################################
# Valid
################################################################################
@pytest.mark.parametrize("value, exp", [
    (1, False),
    (10, False),
    ("1", True),
    ("hello", True),
    (f"smth", True),
    (3.14, False),
])
def test_str_valid(value, exp):
    assert s.valid(s.str, value) == exp, "unexpected"


################################################################################
# Explain
################################################################################
@pytest.mark.parametrize("value, exp", [
    (1, expected_msg("str", "int")),
    (-1, expected_msg("str", "int")),
    (10e2, expected_msg("str", "float")),
    (3.14, expected_msg("str", "float")),
    ("13", None),
    ("def foo(): pass", None),
])
def test_str_explain(value, exp):
    assert s.explain(s.str, value) == exp, "unexpected"


################################################################################
# Conform
################################################################################
@pytest.mark.parametrize("value, exp", [
    (1, "1"),
    (-3.14, "-3.14"),
    ("hello", "hello"),
    ("13", "13"),
    (SometType(), "SomeType")

])
def test_str_conform(value, exp):
    assert s.conform(s.str, value) == exp, "unexpected"
