import pytest
from ghostwriter.utils.cogen.tokenizer import (
    Tokenizer,
    TokenFactory,
    token_label
)

NL = TokenFactory.newline()
EOF = TokenFactory.eof()


@pytest.mark.parametrize("msg, prog, toks", [
    ("simple literal",
     "hello", [
         TokenFactory.literal('hello')
     ]),

    ("literal line",
     "hello\n", [
         TokenFactory.literal('hello'),
         NL
     ]),

    ("two literal lines",
     "hello\nworld", [
         TokenFactory.literal("hello"),
         NL,
         TokenFactory.literal("world")
     ]),

    ("indented lines",
     "   line 1\nline 2\nline 3\n   line 4\n      line 5", [
        TokenFactory.prefix("   "),
        TokenFactory.literal("line 1"),
        NL,
        TokenFactory.literal("line 2"),
        NL,
        TokenFactory.literal("line 3"),
        NL,
        TokenFactory.prefix("   "),
        TokenFactory.literal("line 4"),
        NL,
        TokenFactory.prefix("      "),
        TokenFactory.literal("line 5")
     ]),

    # literals + exprs
    ("literal line with trailing expr",
     "hello <<world>>", [
         TokenFactory.literal('hello '),
         TokenFactory.expr('world')
     ]),

    ("literal, expr, literal with leading whitespace",
     "hello, <<free>> world", [
         TokenFactory.literal("hello, "),
         TokenFactory.expr("free"),
         TokenFactory.literal(" world")
     ]),

    ("leading expr",
     "<<thing>>", [
         TokenFactory.expr("thing")
     ]),

    ("leading expr, followed by literal",
     "<<thing>>!", [
        TokenFactory.expr("thing"),
        TokenFactory.literal("!")
     ]),

    # control lines
    ("control keyword",
     "%for", [TokenFactory.ctrl_kw('for')]),

    ("control keyword - whitespace suffix",
     "%for ", [TokenFactory.ctrl_kw('for')]),

    ("control keyword - whitespace prefix",
     "  %for ", [TokenFactory.prefix('  '), TokenFactory.ctrl_kw('for')]),

    ("control keyword - whitespace between '%' and keyword",
     "% for ", [TokenFactory.ctrl_kw('for')]),

    ("control keyword - prefix, whitespace between '%' and keyword",
     "   % for ", [
        TokenFactory.prefix("   "),
        TokenFactory.ctrl_kw("for")]),

    ("control keyword, newline",
     "%for\n", [TokenFactory.ctrl_kw('for'), NL]),

    ("control keyword, trailing whitespace, newline",
     "%for  \n", [TokenFactory.ctrl_kw('for'), NL]),

    ("control keyword - with args",
     "%for x in [1,2,3,4]",
     [TokenFactory.ctrl_kw('for'), TokenFactory.ctrl_args('x in [1,2,3,4]')]),

    ("control keyword - no args",
     '\n'.join([
         "% foo",
         "hello",
         "% /foo"
     ]), [TokenFactory.ctrl_kw('foo'),
          NL,
          TokenFactory.literal('hello'),
          NL,
          TokenFactory.ctrl_kw('/foo')]),

    ("escaped control string (=> literal)",
     "%% literal", [
        TokenFactory.literal('% literal')]),

    ("escaped control string with prefix (=> literal)",
     "   %% literal", [
        TokenFactory.prefix('   '),
        TokenFactory.literal('% literal')]),

    ("small program",
     '\n'.join([
         "hello <<thing>>",
         "%for x in [1,2,3]",
         "<<x>>!",
         "%/for"]),
     [TokenFactory.literal("hello "),
      TokenFactory.expr("thing"),
      NL,
      TokenFactory.ctrl_kw('for'),
      TokenFactory.ctrl_args('x in [1,2,3]'),
      NL,
      TokenFactory.expr('x'),
      TokenFactory.literal('!'),
      NL,
      TokenFactory.ctrl_kw('/for')])
])
def test_tokenizer(msg, prog, toks):
    p = Tokenizer(prog)
    actual_toks = []
    i = 0
    while True:
        tok = p.next()
        i += 1
        if i > 1000:
            raise RuntimeError("infinite loop prevention - tokenizer seems stuck")
        if tok == EOF:
            break
        actual_toks.append(tok)
    assert actual_toks == toks, msg


# TODO: test tokenizer location()
@pytest.mark.parametrize("msg, prog, positions", [
    ("simple literal",
     "hello", [("LITERAL", 1, 0)]),

    ("line w 2 literals",
     "hello, <<thing>>", [("LITERAL", 1, 0), ("EXPR", 1, 7)]),

    ("two lines",
     "\n".join([
        "hello, <<thing>>",
        "also, hello <<other_thing>>"
     ]), [
         ("LITERAL", 1, 0), ("EXPR", 1, 7), ("NEWLINE", 1, 16),
         ("LITERAL", 2, 0), ("EXPR", 2, 12)]),

    ("for block",
     "\n".join([
        "  % for x in y",
        "    something <<x>>",
        "  % /for"
     ]), [
         ("PREFIX", 1, 0), ("CTRL_KW", 1, 2), ("CTRL_ARGS", 1, 8), ("NEWLINE", 1, 14),
         ("PREFIX", 2, 0), ("LITERAL", 2, 4), ("EXPR", 2, 14), ("NEWLINE", 2, 19),
         ("PREFIX", 3,0), ("CTRL_KW", 3, 2)]),
])
def test_tokenizer_location(msg, prog, positions):
    p = Tokenizer(prog)
    result = []
    i = 0
    print()
    while True:
        tok = p.next()
        i += 1
        if i > 1000:
            raise RuntimeError("infinite loop prevention - tokenizer seems stuck")
        if tok == EOF:
            break
        # print(f"{i} => tok ({repr(tok)}) - loc: ({p.pos_line}, {p.pos_col})")
        result.append((token_label(tok.type), p.pos_line, p.pos_col))
    assert result == positions, msg