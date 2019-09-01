import pytest
from ghostwriter.utils import spec as s


class A:
    pass


tests = [
    None, [], {}, set(), "hello", A()
]


################################################################################
# Valid
################################################################################
@pytest.mark.parametrize("value", tests)
def test_any_valid(value):
    assert s.valid(s.any(), value) == True, "should always be true"


################################################################################
# Explain
################################################################################
@pytest.mark.parametrize("value", tests)
def test_any_explain(value):
    assert s.explain(s.any(), value) is None, "should always pass with no errors"


################################################################################
# Conform
################################################################################
@pytest.mark.parametrize("value", tests)
def test_any_conform(value):
    assert s.conform(s.any(), value) == value, "should always yield the value itself"
