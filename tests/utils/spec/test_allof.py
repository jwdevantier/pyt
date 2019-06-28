import pytest
from pyt.utils import spec as s


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
# All - valid
################################################################################

@pytest.mark.parametrize("value,preds,exp", [
    (10, {'int?': p_isint}, True),
    (10, {'pos?': p_ispos}, True),
    (10, {'neg?': p_isneg}, False),

    # multiple specs - one failure => failure
    (100, {'pos?': p_ispos, 'big?': p_isbig}, True),
    (-100, {'pos?': p_ispos, 'big?': p_isbig}, False),
    (100, {'neg?': p_isneg, 'big?': p_isbig}, False),
    (-100, {'neg?': p_isneg, 'big?': p_isbig}, True),

    # impossible
    (100, {'pos?': p_ispos, 'neg?': p_isneg}, False)
])
def test_allof_valid(value, preds, exp):
    spec = s.allof(preds)
    assert s.valid(spec, value) == exp, "unexpected"


################################################################################
# All - explain
################################################################################

@pytest.mark.parametrize("value,preds,exp", [
    (10, {'int?': p_isint}, None),
    (10, {'pos?': p_ispos}, None),
    (10, {'neg?': p_isneg}, {
        'neg?': "predicate 'isneg' failed"
    }),

    # multiple specs - one failure => failure
    (100, {'pos?': p_ispos, 'big?': p_isbig}, None),
    (-100, {'pos?': p_ispos, 'big?': p_isbig}, {
        'pos?': "predicate 'ispos' failed"
    }),
    (100, {'neg?': p_isneg, 'big?': p_isbig}, {
        'neg?': "predicate 'isneg' failed"
    }),
    (-100, {'neg?': p_isneg, 'big?': p_isbig}, None),

    # impossible
    (100, {'pos?': p_ispos, 'neg?': p_isneg}, {
        'neg?': "predicate 'isneg' failed"
    })
])
def test_allof_explain(value, preds, exp):
    spec = s.allof(preds)
    assert s.explain(spec, value) == exp, "unexpected"

# TODO: missing conform
