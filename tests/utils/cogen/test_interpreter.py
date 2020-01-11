import pytest

from ghostwriter.utils.iwriter import IWriter
from ghostwriter.utils.cogen.interpreter import interpret, Writer
from ghostwriter.utils.cogen.parser import (
    CogenParser, Program, Literal, Expr, Line, CLine, Block, If,
    ParserError, UnexpectedTokenError, InvalidBlockNestingError, InvalidEndBlockArgsError
)
from io import StringIO
import typing as t
from testlib import programs as progs


class BufferWriter(IWriter):
    def __init__(self):
        super().__init__()
        self._buffer = StringIO()

    def write(self, contents: str):
        self._buffer.write(contents)

    def getvalue(self) -> str:
        return self._buffer.getvalue()


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
))
def test_smth(case, example):
    print("start")
    buf: BufferWriter = BufferWriter()
    writer: Writer = Writer(buf)
    interpret(case.ast, writer, example.blocks, example.scope)
    print(buf.getvalue())
    assert buf.getvalue() == example.result, \
        f"{case.header} ({example.header if example.header else '<unnamed>'})"
