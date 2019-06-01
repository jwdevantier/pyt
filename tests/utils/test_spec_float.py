import pytest
from pyt.utils import spec as s


def expected_msg(exp, act):
    return f"expected '{exp}', got '{act}'"


################################################################################
# Valid
################################################################################
@pytest.mark.parametrize("value, exp", [
    (1, False),
    (10, False),
    (10.0, True),
    ("10", False),
    (3.14, True),
    (3.14, True),
])
def test_float_valid(value, exp):
    assert s.valid(s.float, value) == exp, "unexpected"


################################################################################
# Explain
################################################################################
@pytest.mark.parametrize("value, exp", [
    (1, expected_msg("float", "int")),
    (-1, expected_msg("float", "int")),
    (3.14, None),
    (-3.14, None),
    ("13", expected_msg("float", "str")),
])
def test_float_explain(value, exp):
    assert s.explain(s.float, value) == exp, "unexpected"


################################################################################
# Conform
################################################################################
@pytest.mark.parametrize("value, exp", [
    (1, 1.0),
    (-1, -1.0),
    (3.14, 3.14),
    (-3.14, -3.14),
    ("13", 13.0),
    ("abc", s.Invalid),
])
def test_float_conform(value, exp):
    assert s.conform(s.float, value) == exp, "unexpected"