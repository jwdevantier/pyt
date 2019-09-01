import pytest
from ghostwriter.utils import spec as s
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
@pytest.mark.parametrize("msg, value, spec, result", [
    ("unset optional fields should give no errors",
     {},
     {1: StrSpec(), 2: IntSpec()},
     True),
    ("required field should raise error",
     {},
     {1: StrSpec(), 2: s.req(IntSpec())},
     False),
    ("1=>hello should satisfy spec",
     {1: "hello"},
     {1: StrSpec(), 2: IntSpec()},
     True),
    ("1=>2 should fail spec",
     {1: 2},
     {1: StrSpec(), 2: IntSpec()},
     False),
    ("both entries should meet spec",
     {1: "hello", 2: 13},
     {1: StrSpec(), 2: IntSpec()},
     True),
    ("1=>1 should fail spec",
     {1: 1, 2: 13},
     {1: StrSpec(), 2: IntSpec()},
     False),
    ('2=>"13" should fail spec',
     {1: "hello", 2: "13"},
     {1: StrSpec(), 2: IntSpec()},
     False),
])
def test_any_valid(msg, value, spec, result):
    assert s.valid(s.keys(spec), value) == result, msg


################################################################################
# explain
################################################################################
@pytest.mark.parametrize("msg, value, spec, result", [
    ("unset optional fields should give no errors",
     {},
     {1: StrSpec(), 2: IntSpec()},
     None),
    ("required field should raise error",
     {},
     {1: StrSpec(), 2: s.req(IntSpec())},
     {2: "required value missing"}),
    ("1=>hello should satisfy spec",
     {1: "hello"},
     {1: StrSpec(), 2: IntSpec()},
     None),
    ("1=>2 should fail spec",
     {1: 2},
     {1: StrSpec(), 2: IntSpec()},
     {1: s.explain(StrSpec(), 2)}),
    ("both entries should meet spec",
     {1: "hello", 2: 13},
     {1: StrSpec(), 2: IntSpec()},
     None),
    ("1=>1 should fail spec",
     {1: 1, 2: 13},
     {1: StrSpec(), 2: IntSpec()},
     {1: s.explain(StrSpec(), 1)}),
    ('2=>"13" should fail spec',
     {1: "hello", 2: "13"},
     {1: StrSpec(), 2: IntSpec()},
     {2: s.explain(IntSpec(), "13")}),
])
def test_any_explain(msg, value, spec, result):
    assert s.explain(s.keys(spec), value) == result, msg


################################################################################
# conform
################################################################################
@pytest.mark.parametrize("msg, value, spec, result", [
    ("unset optional fields should give no errors",
     {},
     {1: StrSpec(), 2: IntSpec()},
     {}),
    ("extra values should pass through unchanged",
     {'one': 1, 'two': 2},
     {1: StrSpec(), 2: IntSpec()},
     {'one': 1, 'two': 2}),

    ("missing required field => Invalid",
     {},
     {1: StrSpec(), 2: s.req(IntSpec())},
     s.Invalid),

    ("1=>hello should satisfy spec",
     {1: "hello"},
     {1: StrSpec(), 2: IntSpec()},
     {1: "hello"}),
    ("conforms value of '1' to str",
     {1: 2},
     {1: StrSpec(), 2: IntSpec()},
     {1: "2"}),
    ("conforms value of '2' to int",
     {1: "hello", 2: "13"},
     {1: StrSpec(), 2: IntSpec()},
     {1: "hello", 2: 13}),
    ("both entries should meet spec",
     {1: "hello", 2: 13},
     {1: StrSpec(), 2: IntSpec()},
     {1: "hello", 2: 13}),
])
def test_any_explain(msg, value, spec, result):
    assert s.conform(s.keys(spec), value) == result, msg
