import pytest
from pyt.utils import spec as s


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


@pytest.mark.parametrize("value,preds,exp", [
    (A(), A, True),
    (AA(), A, True),
    (A(), AA, False),
    (A(), B, False),

    (AB(), A, True),
    (AB(), B, True)
])
def test_inst_valid(value, preds, exp):
    spec = s.typ(preds)
    assert s.valid(spec, value) == exp, "unexpected"

# TODO: missing explain
# TODO: missing conform
