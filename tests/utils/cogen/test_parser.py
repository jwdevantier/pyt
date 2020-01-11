import pytest
from ghostwriter.utils.cogen.parser import (
    CogenParser, Program, Literal, Expr, Line, CLine, Block, If,
    InvalidEndBlockArgsError
)
from ghostwriter.utils.cogen.tokenizer import (
    Tokenizer
)
from testlib import programs as progs


@pytest.mark.parametrize("case", [
    progs.line_literal,
    progs.line_lit_var,
    progs.if_elif_else,
    progs.for_block,
    progs.component_block,
    progs.prog1,
])
def test_parse_valid_progs(case):
    parser = CogenParser(Tokenizer(case.program))
    print(parser)
    assert parser.parse_program() == case.ast, f"failed: {case.header}"


@pytest.mark.parametrize("msg, prog, err", [
    ("for end-block w arguments",
     "\n".join([
         "%for person in persons",
         "%/for smth"
     ]),
     {'type': InvalidEndBlockArgsError, 'match': ".*'/for' cannot have arguments",
      'line': 2, 'col': 10}),

    ("if end-block w arguments",
     "\n".join([
         "%if a != 2",
         "%/if smth"
     ]),
     {'type': InvalidEndBlockArgsError, 'match': ".*'/if' cannot have arguments",
      'line': 2, 'col': 9})
])
def test_parse_invalid_progs(msg, prog, err):
    """Ensure end block cannot have arguments"""
    parser = CogenParser(Tokenizer(prog))
    with pytest.raises(err['type'], match=err['match']) as excinfo:
        parser.parse_program()
    line = err.get('line')
    col = err.get('col')
    if line:
        assert excinfo.value.location.line == line, "unexpected line"
    if col:
        assert excinfo.value.location.col == col, "unexpected column"

# TODO: '% for', '%/ for' => error
# TODO: '%/if xyz' -- should not be allowed
