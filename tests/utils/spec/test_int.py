import pytest
from ghostwriter.utils import spec as s


def expected_msg(exp, act):
    return f"expected '{exp}', got '{act}'"


################################################################################
# Valid
################################################################################
@pytest.mark.parametrize("value, exp", [
    (1, True),
    (10, True),
    (10.0, False),
    ("10", False),
    (0o10, True),
])
def test_int_valid(value, exp):
    assert s.valid(s.int, value) == exp, "unexpected"


################################################################################
# Explain
################################################################################
@pytest.mark.parametrize("value, exp", [
    (1, None),
    (-1, None),
    (10e2, expected_msg("int", "float")),
    (3.14, expected_msg("int", "float")),
    ("13", expected_msg("int", "str")),
])
def test_int_explain(value, exp):
    assert s.explain(s.int, value) == exp, "unexpected"


################################################################################
# Conform
################################################################################
@pytest.mark.parametrize("value, exp", [
    (1, 1),
    (-1, -1),
    (3.14, 3),
    ("13", 13),
    ("abc", s.Invalid),
])
def test_int_conform(value, exp):
    assert s.conform(s.int, value) == exp, "unexpected"
