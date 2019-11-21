import pytest
import operator
from ghostwriter.utils.cogen.pratt import Parser, Grammar

calc_lang = Grammar()
calc_lang.symbol('end')


@calc_lang.literal('INT')
def handle_int(token):
    return {'value': token.lexeme, 'type': 'INT'}


def math_op(op, left, right):
    return {'binop': op.lexeme, 'left': left, 'right': right}


calc_lang.infix('+', 10)(math_op)
calc_lang.infix('-', 10)(math_op)
calc_lang.infix('*', 20)(math_op)
calc_lang.infix('/', 20)(math_op)


@calc_lang.prefix('neg', 100)
def neg(token, operand):
    return {'uop': operator.neg, 'value': operand}


@calc_lang.enclosing('(', ')', 99)
def parens(tok_begin, tok_end, body):
    return body


@calc_lang.infix_r('EXP', 80)
def exp(operator, left, right):
    return {'binop': '**', 'left': left, 'right': right}


@calc_lang.postfix('INC', 98)
def inc(operator, left):
    return {'uop': lambda n: n + 1, 'value': left}


calc_lang_binop_map = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,
    '**': lambda l, r: l ** r,
}


def calc_lang_interp(node):
    if 'binop' in node:
        return calc_lang_binop_map[node['binop']](
            calc_lang_interp(node['left']),
            calc_lang_interp(node['right']))
    elif 'uop' in node:
        return node['uop'](calc_lang_interp(node['value']))
    elif 'value' in node and node['type'] == 'INT':
        return int(node['value'])

    raise RuntimeError("bad")


class Token:
    def __init__(self, type: str, lexeme: str):
        self.lexeme = lexeme
        self.type = type

    def __repr__(self):
        return f"T<{self.type}, '{self.lexeme}'>"


@pytest.mark.parametrize("test_case, tokens, exp_ast", [
    ("infix_r - right-associative infix operators", [
        Token('INT', '1'),
        Token('EXP', '^'),
        Token('INT', '2'),
        Token('EXP', '^'),
        Token('INT', '3'), ],
     {'binop': '**',
      'left': {'type': 'INT', 'value': '1'},
      'right': {'binop': '**',
                'left': {'type': 'INT', 'value': '2'},
                'right': {'type': 'INT', 'value': '3'}}})
])
def test_parsed_progs_ast(test_case, tokens, exp_ast):
    tokens.append(Token('end', ''))
    parser = Parser(calc_lang, iter(tokens))
    ast = parser.parse()
    assert ast == exp_ast, (
        f"failed test case: {test_case} (prog: {' '.join(tok.lexeme for tok in tokens)})")


@pytest.mark.parametrize("test_case, tokens, result", [
    ("parse int (nud)", [
        Token('INT', '1')],
     1),

    ("parse + (led, binary/infix)", [
        Token('INT', '1'),
        Token('+', '+'),
        Token('INT', '1')],
     2),

    ("negative (nud, unary/prefix -)", [
        Token('neg', '-'),
        Token('INT', '10')],
     -10),

    ("increment (led, postfix)", [
        Token('INT', '10'),
        Token('INC', '++'),],
     11),

    ("operator precedence", [
        Token('INT', '2'),
        Token('+', '+'),
        Token('INT', '3'),
        Token('*', '*'),
        Token('INT', '3')],
     11),

    ("enclosing", [
        Token('(', '('),
        Token('INT', '2'),
        Token('+', '+'),
        Token('INT', '3'),
        Token(')', ')'),
        Token('*', '*'),
        Token('INT', '4')],
     20),

    ("infix_r", [
        Token('INT', '2'),
        Token('EXP', '^'),
        Token('INT', '2'),],
     4)
])
def test_interp_parsed_progs(test_case, tokens, result):
    tokens.append(Token('end', ''))
    parser = Parser(calc_lang, iter(tokens))
    ast = parser.parse()
    assert calc_lang_interp(ast) == result, (
        f"failed test case: {test_case} (prog: {' '.join(tok.lexeme for tok in tokens)})")


@pytest.mark.parametrize("test_case, tokens, expected", [
    ("simple ternary",
     [Token('INT', '2'),
      Token('QUESTION', '?'),
      Token('INT', '1'),
      Token('COLON', ':'),
      Token('INT', '0')],
     {'cond': {'type': 'INT', 'value': '2'},
      'else': {'type': 'INT', 'value': '0'},
      'then': {'type': 'INT', 'value': '1'},
      'type': 'IFEXPR'}),

    ("simple ternary2",
     # 1 < 3 ? 1 : 0
     [Token('INT', '1'),
      Token('LT', '<'),
      Token('INT', '3'),
      Token('QUESTION', '?'),
      Token('INT', '1'),
      Token('COLON', ':'),
      Token('INT', '0')],
     {'cond': {'lhs': {'type': 'INT', 'value': '1'},
               'op': '<',
               'rhs': {'type': 'INT', 'value': '3'},
               'type': 'CMP'},
      'else': {'type': 'INT', 'value': '0'},
      'then': {'type': 'INT', 'value': '1'},
      'type': 'IFEXPR'})
])
def test_ternary(test_case, tokens, expected):
    g = Grammar()
    g.symbol('END')

    @g.literal('INT')
    def g_handle_int(token):
        return {'value': token.lexeme, 'type': 'INT'}

    @g.ternary('QUESTION', 'COLON', 30)
    def g_tern_if(question, colon, cond, true_branch, false_branch):
        return {'type': 'IFEXPR', 'cond': cond, 'then': true_branch, 'else': false_branch}

    @g.infix('LT', 32)
    def g_cmp_lt(op, left, right):
        return {'type': 'CMP', 'op': '<', 'lhs': left, 'rhs': right}

    @g.enclosing('LPAR', 'RPAR', 29)
    def g_parens(tok_begin, tok_end, body):
        return body

    tokens.append(Token('END', ''))
    parser = Parser(g, iter(tokens))
    assert parser.parse() == expected, test_case