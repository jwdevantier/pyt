import pytest
from ghostwriter.utils import spec as s


def expected_msg(exp, act):
    return f"expected '{exp}', got '{act}'"


################################################################################
# Valid
################################################################################
@pytest.mark.parametrize("value, exp", [
    (0, False),
    (1, False),
    (10, False),
    (-1.0, False),
    ("true", False),
    ("True", False),
    ("", False),
    (False, True),
    (True, True),
])
def test_bool_valid(value, exp):
    assert s.valid(s.bool, value) == exp, "unexpected"


################################################################################
# Explain
################################################################################
@pytest.mark.parametrize("value, exp", [
    (0, expected_msg("bool", "int")),
    (1, expected_msg("bool", "int")),
    (10, expected_msg("bool", "int")),
    (-1.0, expected_msg("bool", "float")),
    ("true", expected_msg("bool", "str")),
    ("True", expected_msg("bool", "str")),
    ("", expected_msg("bool", "str")),
    (False, None),
    (True, None),
])
def test_bool_explain(value, exp):
    assert s.explain(s.bool, value) == exp, "unexpected"


################################################################################
# Conform
################################################################################
@pytest.mark.parametrize("value, exp", [
    (0, False),
    (1, True),
    (10, True),
    (-1.0, True),
    ("true", True),
    ("True", True),
    ("", False),
    (False, False),
    (True, True),
])
def test_bool_conform(value, exp):
    assert s.conform(s.bool, value) == exp, "unexpected"