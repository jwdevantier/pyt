import typing as t

import pytest
from ghostwriter.utils import spec as s


################################################################################
# InSeq - valid
################################################################################
@pytest.mark.parametrize("msg, value, seq, result", [
    ("first elem",
     'debug',
     ['debug', 'info', 'warning', 'error', 'critical'],
     True),
    ("ok - third element",
     'warning',
     ['debug', 'info', 'warning', 'error', 'critical'],
     True),
    ("not in collection",
     'whatever',
     ['debug', 'info', 'warning', 'error', 'critical'],
     False),
])
def test_inseq_valid(msg, value, seq, result):
    assert s.valid(s.inseq(seq), value) == result, msg


################################################################################
# InSeq - explain
################################################################################
@pytest.mark.parametrize("msg, value, seq, errmsg", [
    ("first elem",
     'debug',
     ['debug', 'info', 'warning', 'error', 'critical'],
     None),
    ("ok - third element",
     'warning',
     ['debug', 'info', 'warning', 'error', 'critical'],
     None),
    ("not in collection",
     'whatever',
     ['debug', 'info', 'warning', 'error', 'critical'],
     "value not in"),
])
def test_inseq_explain(msg, value, seq, errmsg):
    out = s.explain(s.inseq(seq), value)
    if errmsg:
        assert errmsg in out, msg
    else:
        assert out is None


################################################################################
# InSeq - conform
################################################################################
@pytest.mark.parametrize("msg, value, seq, result", [
    ("first elem",
     'debug',
     ['debug', 'info', 'warning', 'error', 'critical'],
     'debug'),
    ("ok - third element",
     'warning',
     ['debug', 'info', 'warning', 'error', 'critical'],
     'warning'),
    ("not in collection",
     'whatever',
     ['debug', 'info', 'warning', 'error', 'critical'],
     s.Invalid),
])
def test_inseq_conform(msg, value, seq, result):
    assert s.conform(s.inseq(seq), value) == result, msg
