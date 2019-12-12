import pytest
import operator
from ghostwriter.utils.cogen.pratt import Parser, Grammar

T_END = 0
T_INT = 1
T_ADD = 2
T_SUB = 3
T_MUL = 4
T_DIV = 5
T_NEG = 6
T_INC = 7
T_EXP = 8
T_QUESTION = 9
T_COLON = 10
T_LT = 11
T_LPAR = 12
T_RPAR = 13


calc_lang = Grammar()
calc_lang.symbol(T_END)


@calc_lang.literal(T_INT)
def handle_int(token):
    return {'value': token.lexeme, 'type': 'INT'}


def math_op(op, left, right):
    return {'binop': op.lexeme, 'left': left, 'right': right}


calc_lang.infix(T_ADD, 10)(math_op)
calc_lang.infix(T_SUB, 10)(math_op)
calc_lang.infix(T_MUL, 20)(math_op)
calc_lang.infix(T_DIV, 20)(math_op)


@calc_lang.prefix(T_NEG, 100)
def neg(token, operand):
    return {'uop': operator.neg, 'value': operand}


@calc_lang.enclosing(T_LPAR, T_RPAR, 99)
def parens(tok_begin, tok_end, body):
    return body


@calc_lang.infix_r(T_EXP, 80)
def exp(operator, left, right):
    return {'binop': '**', 'left': left, 'right': right}


@calc_lang.postfix(T_INC, 98)
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
    def __init__(self, type: int, lexeme: str):
        self.lexeme = lexeme
        self.type = type

    def __repr__(self):
        return f"T<{self.type}, '{self.lexeme}'>"


@pytest.mark.parametrize("test_case, tokens, result", [
    ("parse int (nud)", [
        Token(T_INT, '1')],
     1),

    ("parse + (led, binary/infix)", [
        Token(T_INT, '1'),
        Token(T_ADD, '+'),
        Token(T_INT, '1')],
     2),

    ("negative (nud, unary/prefix -)", [
        Token(T_NEG, '-'),
        Token(T_INT, '10')],
     -10),

    ("increment (led, postfix)", [
        Token(T_INT, '10'),
        Token(T_INC, '++'),],
     11),

    ("operator precedence", [
        Token(T_INT, '2'),
        Token(T_ADD, '+'),
        Token(T_INT, '3'),
        Token(T_MUL, '*'),
        Token(T_INT, '3')],
     11),

    ("enclosing", [
        Token(T_LPAR, '('),
        Token(T_INT, '2'),
        Token(T_ADD, '+'),
        Token(T_INT, '3'),
        Token(T_RPAR, ')'),
        Token(T_MUL, '*'),
        Token(T_INT, '4')],
     20),

    ("infix_r", [
        Token(T_INT, '2'),
        Token(T_EXP, '^'),
        Token(T_INT, '2'),],
     4)
])
def test_interp_parsed_progs(test_case, tokens, result):
    tokens.append(Token(T_END, ''))
    parser = Parser(calc_lang, iter(tokens))
    ast = parser.parse()
    assert calc_lang_interp(ast) == result, (
        f"failed test case: {test_case} (prog: {' '.join(tok.lexeme for tok in tokens)})")


@pytest.mark.parametrize("test_case, tokens, exp_ast", [
    ("infix_r - right-associative infix operators", [
        Token(T_INT, '1'),
        Token(T_EXP, '^'),
        Token(T_INT, '2'),
        Token(T_EXP, '^'),
        Token(T_INT, '3'), ],
     {'binop': '**',
      'left': {'type': 'INT', 'value': '1'},
      'right': {'binop': '**',
                'left': {'type': 'INT', 'value': '2'},
                'right': {'type': 'INT', 'value': '3'}}})
])
def test_parsed_progs_ast(test_case, tokens, exp_ast):
    tokens.append(Token(T_END, ''))
    parser = Parser(calc_lang, iter(tokens))
    ast = parser.parse()
    assert ast == exp_ast, (
        f"failed test case: {test_case} (prog: {' '.join(tok.lexeme for tok in tokens)})")


@pytest.mark.parametrize("test_case, tokens, expected", [
    ("simple ternary",
     [Token(T_INT, '2'),
      Token(T_QUESTION, '?'),
      Token(T_INT, '1'),
      Token(T_COLON, ':'),
      Token(T_INT, '0')],
     {'cond': {'type': 'INT', 'value': '2'},
      'else': {'type': 'INT', 'value': '0'},
      'then': {'type': 'INT', 'value': '1'},
      'type': 'IFEXPR'}),

    ("simple ternary2",
     # 1 < 3 ? 1 : 0
     [Token(T_INT, '1'),
      Token(T_LT, '<'),
      Token(T_INT, '3'),
      Token(T_QUESTION, '?'),
      Token(T_INT, '1'),
      Token(T_COLON, ':'),
      Token(T_INT, '0')],
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
    g.symbol(T_END)

    @g.literal(T_INT)
    def g_handle_int(token):
        return {'value': token.lexeme, 'type': 'INT'}

    @g.ternary(T_QUESTION, T_COLON, 30)
    def g_tern_if(question, colon, cond, true_branch, false_branch):
        return {'type': 'IFEXPR', 'cond': cond, 'then': true_branch, 'else': false_branch}

    @g.infix(T_LT, 32)
    def g_cmp_lt(op, left, right):
        return {'type': 'CMP', 'op': '<', 'lhs': left, 'rhs': right}

    @g.enclosing(T_LPAR, T_RPAR, 29)
    def g_parens(tok_begin, tok_end, body):
        return body

    tokens.append(Token(T_END, ''))
    parser = Parser(g, iter(tokens))
    assert parser.parse() == expected, test_case
