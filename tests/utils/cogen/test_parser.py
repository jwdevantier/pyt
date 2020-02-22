import pytest
from ghostwriter.utils.cogen.parser import (
    CogenParser,
    UnhandledTokenError, IndentationError
)
from ghostwriter.utils.cogen.tokenizer import (
    Tokenizer
)
from testlib import programs as progs


@pytest.mark.parametrize("case", [
    progs.line_literal_simplest,
    progs.line_lit_var,
    progs.line_expr_first,
    progs.line_lit_adv,
    progs.if_simplest,
    progs.if_elif_else,
    progs.for_block_simplest,
    progs.for_block_use_var,
    progs.component_block_simplest,
    progs.component_block_simple_var,
    progs.component_block_simple_var_from_scope,
    progs.indent_text_lines,
    progs.indent_is_wysiwyg_if,
    progs.indent_is_wysiwyg_for,
    progs.indent_component_1,
    progs.indent_component_block_to_ctrl_line,
    progs.body_block_simplest,
    progs.body_block_nested,
    progs.component_block_w_body,
])
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
