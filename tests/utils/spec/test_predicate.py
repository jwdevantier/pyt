import pytest
from pyt.utils import spec as s


################################################################################
# Predicate
################################################################################
@pytest.mark.parametrize("value,result,txt", [
    (10, True, "is an int"),
    (2, True, "is an int"),
    (-1, True, "is an int"),
    (2.2, False, "floats a not ints"),
    ("hello", False, "str is not an int"),
    ("2", False, "str is not an int")
])
def test_predicate_int_valid(value, result, txt):
    ps = s.predicate(lambda x: isinstance(x, int), "isint")
    assert s.valid(ps, value) == result, f"valid({value}): {txt}"


@pytest.mark.parametrize("value,result", [
    (10, 10),
    (2, 2),
    (-1, -1),
    (2.2, 2),
    ("hello", s.Invalid),
    ("2", 2)
])
def test_predicate_int_conform(value, result):
    ps = s.predicate(lambda x: int(x), "intify")
    assert s.conform(ps, value) == result, f"conform({value}) failed - expected {result}"


@pytest.mark.parametrize("value,success", [
    (10, True),
    (2, True),
    (-1, True),
    (2.2, False),
    ("hello", False),
    ("2", False)
])
def test_predicate_int_explain(value, success):
    ps = s.predicate(lambda x: isinstance(x, int), "isint")
    if success:
        assert s.explain(ps, value) is None, f"expected isint({value}) to succeed"
    else:
        assert s.explain(ps, value) == f"predicate 'isint' failed"


################################################################################
# Natural Integer Example
################################################################################
# Arose from a bug discovered when writing a spec.
#
# Success:  any non-False value returned from the predicat function
#
#           valid: True
#           conform: <the actual value>
#           explain: None
#
# Error:    if the predicate function returns False or raises an exception
#
#           valid: False
#           conform: Invalid
#           explain: <some string explaining the failure>

@pytest.mark.parametrize("input, exp_valid, exp_conform, exp_explain", [
    (1, True, 1, False),
    (-1, False, s.Invalid, True)
])
def test_natint(input, exp_valid, exp_conform, exp_explain):
    def _natint(value):
        value = int(value)
        return value if value > 0 else False
    spec = s.predicate(_natint, 'natural integer')
    assert s.valid(spec, input) == exp_valid, "validation failed"
    assert s.conform(spec, input) == exp_conform, "conform value is incorrect"
    assert s.explain(spec, input) == ("predicate 'natural integer' failed" if exp_explain else None)