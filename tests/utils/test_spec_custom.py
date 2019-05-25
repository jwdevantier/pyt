import pytest
from pyt.utils import spec as s
import typing as t


# Test wrote in response to unexpected bug where cython code essentially
# ignores the methods defined in classes extending the cdef class (extention
# type).

# TODO: move tests using IntSpec out to its own test file.
class IntSpec(s.Spec):
    @staticmethod
    def _valid(value: t.Any):
        return isinstance(value, int)

    @staticmethod
    def _explain(value: t.Any):
        if not isinstance(value, int):
            return f"expected 'int', got '{type(value)}'"

    @staticmethod
    def _conform(value: t.Any):
        try:
            return int(value)
        except (ValueError, TypeError):
            return s.Invalid

    @staticmethod
    def _name():
        return "Int"


@pytest.mark.parametrize("value, element_spec, exp", [

    # custom spec
    ([1, 2, 3], IntSpec(), True),
    ([1, "2", 3], IntSpec(), False),
])
def test_inst_valid(value, element_spec, exp):
    spec = s.seqof(element_spec)
    assert s.valid(spec, value) == exp, "expected direct call to work"


@pytest.mark.parametrize("value, element_spec, exp", [
    # custom spec
    ([1, 2, 3], IntSpec(), [1, 2, 3]),
    ([1, "2", 3], IntSpec(), [1, 2, 3])
])
def test_inst_valid(value, element_spec, exp):
    spec = s.seqof(element_spec)
    assert s.conform(spec, value) == exp, "call from C-code to resolve correctly"
