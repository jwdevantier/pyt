import pytest
from testlib.bufferwriter import BufferWriter

from ghostwriter.utils.cogen.interpreter import interpret, Writer
# from ghostwriter.utils.cogen.parser import (
#     CogenParser, Program, Literal, Expr, Line, Block, If,
#     ParserError, UnhandledTokenError, InvalidBlockNestingError, InvalidEndBlockArgsError
# )
from io import StringIO
import typing as t
from testlib import programs as progs


# TODO: write fn to generate full list of tests (essentially unrolling the loop so each test is shown in the output)
def collect_testcase_examples(*testcases: progs.TestCase)\
        -> t.Generator[t.Tuple[progs.TestCase, progs.Example], None, None]:
    test_num = 0
    for testcase in testcases:
        test_num += 1
        example_num = 0
        if len(testcase.examples) == 0:
            raise RuntimeError(f"{testcase} has no examples! Remove case from list or write examples to use")
        for example in testcase.examples:
            example_num += 1
            # http://doc.pytest.org/en/latest/example/parametrize.html
            yield pytest.param(testcase, example, id=f"{test_num} - {testcase.header}#{example_num}")


@pytest.mark.parametrize("case, example", collect_testcase_examples(
    progs.line_literal_simplest,
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
    progs.component_block_w_body,
    progs.indent_lines_text,
    progs.indent_lines_expr,
    progs.indent_if_toplevel,
    progs.indent_block_toplevel,
    progs.indent_component_1_flat_component,
    progs.indent_component_2_indented_body_block,
))
def test_interpret_valid_progs(case, example):
    buf: BufferWriter = BufferWriter()
    writer: Writer = Writer(buf)
    interpret(case.ast, writer, example.blocks, example.scope)
    print(buf.getvalue())
    assert buf.getvalue() == example.result, \
        f"{case.header} ({example.header if example.header else '<unnamed>'})"
