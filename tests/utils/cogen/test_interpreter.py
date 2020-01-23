import pytest
from testlib.bufferwriter import BufferWriter

from ghostwriter.utils.cogen.interpreter import interpret, Writer
from ghostwriter.utils.cogen.parser import (
    CogenParser, Program, Literal, Expr, Line, CLine, Block, If,
    ParserError, UnexpectedTokenError, InvalidBlockNestingError, InvalidEndBlockArgsError
)
from io import StringIO
import typing as t
from testlib import programs as progs


# TODO: write fn to generate full list of tests (essentially unrolling the loop so each test is shown in the output)
def collect_testcase_examples(*testcases: progs.TestCase)\
        -> t.Generator[t.Tuple[progs.TestCase, progs.Example], None, None]:
    for testcase in testcases:
        if len(testcase.examples) == 0:
            raise RuntimeError(f"{testcase} has no examples! Remove case from list or write examples to use")
        for example in testcase.examples:
            yield testcase, example


@pytest.mark.parametrize("case, example", collect_testcase_examples(
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
    progs.indent_if_block_to_ctrl_line,
    progs.indent_for_block_to_ctrl_line,
    progs.indent_component_block_to_ctrl_line,
    progs.component_block_w_body,
))
def test_smth(case, example):
    buf: BufferWriter = BufferWriter()
    writer: Writer = Writer(buf)
    interpret(case.ast, writer, example.blocks, example.scope)
    print(buf.getvalue())
    assert buf.getvalue() == example.result, \
        f"{case.header} ({example.header if example.header else '<unnamed>'})"
