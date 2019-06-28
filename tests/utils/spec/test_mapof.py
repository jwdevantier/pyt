import pytest
from pyt.utils import spec as s
import typing as t


class IntSpec(s.SpecBase):
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


class StrSpec(s.SpecBase):
    @staticmethod
    def _valid(value: t.Any):
        return isinstance(value, str)

    @staticmethod
    def _explain(value: t.Any):
        if not isinstance(value, str):
            return f"expected 'str', got '{type(value).__name__}'"

    @staticmethod
    def _conform(value: t.Any):
        return str(value)

    @staticmethod
    def _name():
        return "Str"


################################################################################
# Valid
################################################################################
@pytest.mark.parametrize("value, exp", [
    ({1: 1, 2: 2}, False),
    ({1: 1, 2: 2.2}, False),
    ([1, 2], False),
    ("hello", False),
    ({"1": 1}, True),
    ({"1": 1, "2": 2}, True),
])
def test_mapof_valid(value, exp):
    spec = s.mapof(StrSpec(), IntSpec())
    assert s.valid(spec, value) == exp, "unexpected"


################################################################################
# Explain
################################################################################
@pytest.mark.parametrize("value, exp", [
    ({"1": 1, "2": 2}, None),
    ({1: 1, 2: 2}, {
        1: {'key': s.explain(StrSpec(), 1)},
        2: {'key': s.explain(StrSpec(), 2)}
    }),
    ({1: 1, 2: 2.2}, {
        1: {'key': s.explain(StrSpec(), 1)},
        2: {'key': s.explain(StrSpec(), 2),
            'value': s.explain(IntSpec(), 2.2)}
    })
])
def test_mapof_explain(value, exp):
    spec = s.mapof(StrSpec(), IntSpec())
    assert s.explain(spec, value) == exp, "unexpected"


################################################################################
# Conform
################################################################################
@pytest.mark.parametrize("value, exp", [
    ({"1": 1, "2": 2}, {"1": 1, "2": 2}),
    ({1: 1, 2: 2}, {"1": 1, "2": 2}),
    ({1: 1, 2: 2.2}, {"1": 1, "2": 2}),
    ("hello", s.Invalid),
    ({"1": "oops"}, s.Invalid),
])
def test_mapof_conform(value, exp):
    spec = s.mapof(StrSpec(), IntSpec())
    assert s.conform(spec, value) == exp, "unexpected"
