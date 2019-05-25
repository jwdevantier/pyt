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

# TODO: missing conform
