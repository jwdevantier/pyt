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


################################################################################
# Opt - valid
################################################################################
@pytest.mark.parametrize("msg, value, spec, result", [
    ("should be a valid int",
     1,
     IntSpec(),
     True),
    ("should be invalid - None is not an int",
     None,
     IntSpec(),
     False),
    ("should be OK - optional value",
     None,
     s.opt(IntSpec()),
     True),

    ('fallback - give regular int',
     None,
     s.opt(IntSpec(), 3),
     True),
])
def test_opt_valid(msg, value, spec, result):
    assert s.valid(spec, value) == result, msg


# Cannot create a spec where the default/fallback value does NOT conform to spec
def test_opt_raise_valueerror():
    with pytest.raises(ValueError):
        s.opt(IntSpec(), "3")


################################################################################
# Opt - explain
################################################################################
@pytest.mark.parametrize("msg, value, spec, result", [
    ("should be a valid int",
     1,
     IntSpec(),
     None),

    ("None is not an int",
     None,
     IntSpec(),
     s.explain(IntSpec(), None)),

    ("should be an optional value",
     None,
     s.opt(IntSpec()),
     None),

    ('fallback - give regular int',
     None,
     s.opt(IntSpec(), 3),
     None),
])
def test_opt_explain(msg, value, spec, result):
    assert s.explain(spec, value) == result, msg


################################################################################
# Opt - conform
################################################################################
@pytest.mark.parametrize("msg, value, spec, result", [
    ("should be a valid int",
     1,
     IntSpec(),
     1),
    ("None is not an int",
     None,
     IntSpec(),
     s.Invalid),
    ("should be an optional value",
     None,
     s.opt(IntSpec()),
     None),

    ('can conform "3" to 3',
     "3",
     s.opt(IntSpec()),
     3),
    ('can conform 3.3 to 3',
     3.3,
     s.opt(IntSpec()),
     3),

    ('fallback - give regular int',
     None,
     s.opt(IntSpec(), 3),
     3),
])
def test_opt_explain(msg, value, spec, result):
    assert s.conform(spec, value) == result, msg
