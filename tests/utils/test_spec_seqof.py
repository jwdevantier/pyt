import typing as t

import pytest
from pyt.utils import spec as s

p_isint = s.predicate(lambda v: isinstance(v, int))
p_isstr = s.predicate(lambda v: isinstance(v, str))


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


################################################################################
# SeqOf - valid
################################################################################
# NOTE: this is utterly reliant on spec Predicate working
@pytest.mark.parametrize("value, element_spec, exp", [

    # int predicate
    ([1, 2, 3], p_isint, True),
    ([1, 2, 3, 3.2], p_isint, False),

    # str predicate
    (["one", "two", "three"], p_isstr, True),

    # custom spec
    ([1, 2, 3], IntSpec(), True),

    # tuples - also a form of sequences
    ((1, 2, 8), p_isint, True),
    ((1, 2, 3, 3.2), p_isint, False),
])
def test_inst_valid(value, element_spec, exp):
    spec = s.seqof(element_spec)
    assert s.valid(spec, value) == exp, "unexpected"


################################################################################
# SeqOf - explain
################################################################################
# NOTE: this is utterly reliant on spec Predicate working
@pytest.mark.parametrize("value, exp", [
    # int predicate
    ([1, 2, 3], [1, 2, 3]),
    ([1, 2, 3, 4.2], [1, 2, 3, 4]),
    ([1, "2", 3], [1, 2, 3])
])
def test_inst_explain(value, exp):
    spec = s.seqof(s.predicate(lambda v: int(v)))
    assert s.conform(spec, value) == exp, "unexpected"


################################################################################
# SeqOf - conform
################################################################################
@pytest.mark.parametrize("value, element_spec, exp", [
    ([1, 2, 3], IntSpec(), [1, 2, 3]),
    ([1, "2", 3], IntSpec(), [1, 2, 3]),
    ([1, 2, 3.5], IntSpec(), [1, 2, 3]),
])
def test_inst_conform(value, element_spec, exp):
    spec = s.seqof(element_spec)
    assert s.conform(spec, value) == exp, "unexpected"
