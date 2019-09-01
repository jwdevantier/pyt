import pytest
from ghostwriter.utils import spec as s


# !! These tests rely on the 'Predicate' spec functioning

def isint(v):
    return isinstance(v, int)


p_isint = s.predicate(isint)


def isbig(v):
    return isinstance(v, int) and abs(v) >= 10


p_isbig = s.predicate(isbig)


def ispos(v):
    return isinstance(v, int) and v > 0


p_ispos = s.predicate(ispos)


def isneg(v):
    return isinstance(v, int) and v < 0


p_isneg = s.predicate(isneg)


################################################################################
# Any - Valid
################################################################################
@pytest.mark.parametrize("value,preds,exp", [
    (10, {'int?': p_isint}, True),
    (10, {'pos?': p_ispos}, True),
    (10, {'neg?': p_isneg}, False),

    # multiple specs - one success => success
    (7, {'neg?': p_isneg, 'big?': p_isbig}, False),
    (-7, {'neg?': p_isneg, 'big?': p_isbig}, True),
    (17, {'neg?': p_isneg, 'big?': p_isbig}, True),
])
def test_anyof_valid(value, preds, exp):
    spec = s.anyof(preds)
    assert s.valid(spec, value) == exp, "unexpected"


################################################################################
# Any - Explain
################################################################################
@pytest.mark.parametrize("value,preds,exp", [
    (10, {'int?': p_isint}, None),
    (10, {'pos?': p_ispos}, None),
    (10, {"neg?": p_isneg}, {
        'neg?': "predicate 'isneg' failed"
    }),

    # multiple specs - one success => success
    (7, {'neg?': p_isneg, 'big?': p_isbig}, {
        'neg?': "predicate 'isneg' failed",
        'big?': "predicate 'isbig' failed"
    }),
    (-7, {'neg?': p_isneg, 'big?': p_isbig}, None),
    (17, {'neg?': p_isneg, 'big?': p_isbig}, None),
])
def test_anyof_explain(value, preds, exp):
    spec = s.anyof(preds)
    assert s.explain(spec, value) == exp, "unexpected"

# TODO: missing conform
