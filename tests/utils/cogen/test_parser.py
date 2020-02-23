import typing as t
import pytest
from ghostwriter.utils.cogen.parser import (
    CogenParser,
    UnhandledTokenError, IndentationError
)
from ghostwriter.utils.cogen.tokenizer import (
    Tokenizer
)
from testlib import programs as progs


def name_testcases(*testcases: progs.TestCase)\
        -> t.Generator[t.Tuple[progs.TestCase, progs.Example], None, None]:
    test_num = 0
    for testcase in testcases:
        test_num += 1
        # http://doc.pytest.org/en/latest/example/parametrize.html
        yield pytest.param(testcase, id=f"{test_num} - {testcase.header}")


@pytest.mark.parametrize("case", name_testcases(
    progs.line_literal_simplest,
    progs.line_literal_escaped,
    progs.line_literal_indented,
    progs.line_lit_var,
    progs.line_expr_first,
    progs.line_lit_adv,
    progs.line_exprs_side_by_side,
    progs.if_simplest,
    progs.if_elif_else,
    progs.for_block_simplest,
    progs.for_block_use_var,
    progs.component_block_simplest,
    progs.component_block_scope_arg,
    progs.component_block_scope_inherited,
    progs.body_block_simplest,
    progs.body_block_nested,
    progs.component_block_w_body,
    progs.indent_lines_text,
    progs.indent_lines_expr,
    progs.indent_if_toplevel,
    progs.indent_block_toplevel,
    progs.indent_component_1_flat_component,
    progs.indent_component_2_indented_body_block))
def test_parse_valid_progs(case):
    parser = CogenParser(Tokenizer(case.program))
    print(parser)
    # strangely, will show up with case.ast as Expected
    assert parser.parse_program() == case.ast, f"failed: {case.header}"


@pytest.mark.parametrize("msg, prog, err", [
    ("/<block> w args - top-level",
     "\n".join([
         "%for person in persons",
         "%/for smth"
     ]),
     {'type': UnhandledTokenError, 'match': ".*",
      'line': 2, 'col': 10}),

    ("/<block> w args - nested",
     "\n".join([
         "% foo",
         "%for person in persons",
         "%/for smth",
         "% /foo"
     ]),
     {'type': UnhandledTokenError, 'match': ".*",
      'line': 3, 'col': 10}),

    ("/if w args - top-level",
     "\n".join([
         "%if a != 2",
         "%/if smth"
     ]),
     {'type': UnhandledTokenError, 'match': ".*",
      'line': 2, 'col': 9}),

    ("/if w args - nested",
     "\n".join([
         "% foo",
         "%if a != 2",
         "%/if smth",
         "% /foo"
     ]),
     {'type': UnhandledTokenError, 'match': ".*",
      'line': 3, 'col': 9}),

    # Case: indentation test - enforce line indentation
    ###################################################################
    # Each line should be indented at least as their surrounding block,
    # but may be indented further still.

    ("indentation - <block> - line indent - top-level",
     "\n".join([
         "   %for x in y",
         "   hello",
         "     something",
         "  new",
         "   %/for"
     ]),
     {'type': IndentationError, 'match': ".*line's indentation.*",
      'line': 4, 'col': 5}),

    ("indentation - <block> - line indent - nested",
     "\n".join([
         "   % parent",
         "     %for x in y",
         "     hello",
         "       something",
         "    new",
         "     % /for",
         "   % /parent"
     ]),
     {'type': IndentationError, 'match': ".*line's indentation.*",
      'line': 5, 'col': 7}),

    ("indentation - if-block - line indent - top-level",
     "\n".join([
         "   %if x > y",
         "   hello",
         "     something",
         "  new",
         "   %/if"
     ]),
     {'type': IndentationError, 'match': ".*line's indentation.*",
      'line': 4, 'col': 5}),

    ("indentation - if-block - line indent - nested",
     "\n".join([
         "   % parent",
         "     %if x > y",
         "     hello",
         "       something",
         "    new",
         "     % /if",
         "   % /parent"
     ]),
     {'type': IndentationError, 'match': ".*line's indentation.*",
      'line': 5, 'col': 7}),

    # Case: indentation test - enforce block close indentation
    ###################################################################
    # Each line should be indented at least as their surrounding block,
    # but may be indented further still.
    ("indentation - /<block> - too little indentation",
     "\n".join([
         "   % parent",
         "     xxxx",
         "   %for x in y",
         "     hello",
         "       something",
         "    new",
         "  % /for",
         "   % /parent"
     ]),
     {'type': IndentationError, 'match': ".*",
      'line': 7, 'col': 8}),

    ("indentation - /<block> - too much indentation",
     "\n".join([
         "   % parent",
         "     xxxx",
         "   %for x in y",
         "     hello",
         "       something",
         "    new",
         "    % /for",
         "   % /parent"
     ]),
     {'type': IndentationError, 'match': ".*",
      'line': 7, 'col': 10}),

    # TODO: elif, else tests
    ("indentation - %elif - too little indentation",
     "\n".join([
         "   % parent",
         "     xxxx",
         "      % if x > 10",
         "      x is greater than 10",
         "    % elif x > 5",
         "      x is larger than 5, less than 11",
         "      % else",
         "      x is 5 or less",
         "      % /if",
         "   % /parent"
     ]),
     {'type': IndentationError, 'match': ".*all condition blocks.*",
      'line': 5, 'col': 10}),

    ("indentation - %elif - too much indentation",
     "\n".join([
         "   % parent",
         "     xxxx",
         "      % if x > 10",
         "      x is greater than 10",
         "        % elif x > 5",
         "      x is larger than 5, less than 11",
         "      % else",
         "      x is 5 or less",
         "      % /if",
         "   % /parent"
     ]),
     {'type': IndentationError, 'match': ".*all condition blocks.*",
      'line': 5, 'col': 14}),

    ("indentation - %else - too little indentation",
     "\n".join([
         "   % parent",
         "     xxxx",
         "      % if x > 10",
         "      x is greater than 10",
         "      % elif x > 5",
         "      x is larger than 5, less than 11",
         "    % else",
         "      x is 5 or less",
         "      % /if",
         "   % /parent"
     ]),
     {'type': IndentationError, 'match': ".*all condition blocks.*",
      'line': 7, 'col': 10}),

    ("indentation - %else - too much indentation",
     "\n".join([
         "   % parent",
         "     xxxx",
         "      % if x > 10",
         "      x is greater than 10",
         "      % elif x > 5",
         "      x is larger than 5, less than 11",
         "        % else",
         "      x is 5 or less",
         "      % /if",
         "   % /parent"
     ]),
     {'type': IndentationError, 'match': ".*all condition blocks.*",
      'line': 7, 'col': 14}),
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
