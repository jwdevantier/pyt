import pytest
from ghostwriter.utils import spec as s


class A:
    pass


class AA(A):
    pass


class AAA(AA):
    pass


class B:
    pass


class BB(B):
    pass


class AB(A, B):
    pass


################################################################################
# Typ - valid
################################################################################
@pytest.mark.parametrize("msg, value, typ, result", [
    ("A is A",
     A(), A, True),
    ("AA is also A",
     AA(), A, True),
    ("A is not an AA",
     A(), AA, False),
    ("A is not a B",
     A(), B, False),

    ("AB is an A",
     AB(), A, True),
    ("AB is a B",
     AB(), B, True)
])
def test_typ_valid(msg, value, typ, result):
    assert s.valid(s.type(typ), value) == result, msg


################################################################################
# Typ - explain
################################################################################
@pytest.mark.parametrize("msg, value, typ, result", [
    ("A is A",
     A(), A,
     None),
    ("AA is also A",
     AA(), A,
     None),
    ("A is not an AA",
     A(), AA,
     f"expected instance of '{AA.__name__}', got '{A.__name__}'"),
    ("A is not a B",
     A(), B,
     f"expected instance of '{B.__name__}', got '{A.__name__}'"),

    ("AB is an A",
     AB(), A,
     None),
    ("AB is a B",
     AB(), B,
     None)
])
def test_typ_explain(msg, value, typ, result):
    assert s.explain(s.type(typ), value) == result, msg


################################################################################
# Typ - conform
################################################################################

oA = A()
oAA = AA()
oAB = AB()


@pytest.mark.parametrize("msg, value, typ, result", [
    ("A is A",
     oA, A,
     oA),
    ("AA is also A",
     oAA, A,
     oAA),
    ("A is not an AA",
     oA, AA,
     s.Invalid),
    ("A is not a B",
     oA, B,
     s.Invalid),

    ("AB is an A",
     oAB, A,
     oAB),
    ("AB is a B",
     oAB, B,
     oAB)
])
def test_typ_explain(msg, value, typ, result):
    assert s.conform(s.type(typ), value) == result, msg
