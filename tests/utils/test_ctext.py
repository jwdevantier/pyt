import pytest
from ghostwriter.utils.ctext import deindent_block
from ghostwriter.utils.text import deindent_str_block
import timeit


norvig_lispy_dedented = """\
################ Lispy: Scheme Interpreter in Python

## (c) Peter Norvig, 2010-16; See http://norvig.com/lispy.html

from __future__ import division
import math
import operator as op

################ Types

Symbol = str          # A Lisp Symbol is implemented as a Python str
List   = list         # A Lisp List is implemented as a Python list
Number = (int, float) # A Lisp Number is implemented as a Python int or float

################ Parsing: parse, tokenize, and read_from_tokens

def parse(program):
    "Read a Scheme expression from a string."
    return read_from_tokens(tokenize(program))

def tokenize(s):
    "Convert a string into a list of tokens."
    return s.replace('(',' ( ').replace(')',' ) ').split()

def read_from_tokens(tokens):
    "Read an expression from a sequence of tokens."
    if len(tokens) == 0:
        raise SyntaxError('unexpected EOF while reading')
    token = tokens.pop(0)
    if '(' == token:
        L = []
        while tokens[0] != ')':
            L.append(read_from_tokens(tokens))
        tokens.pop(0) # pop off ')'
        return L
    elif ')' == token:
        raise SyntaxError('unexpected )')
    else:
        return atom(token)

def atom(token):
    "Numbers become numbers; every other token is a symbol."
    try: return int(token)
    except ValueError:
        try: return float(token)
        except ValueError:
            return Symbol(token)

################ Environments

def standard_env():
    "An environment with some Scheme standard procedures."
    env = Env()
    env.update(vars(math)) # sin, cos, sqrt, pi, ...
    env.update({
        '+':op.add, '-':op.sub, '*':op.mul, '/':op.truediv, 
        '>':op.gt, '<':op.lt, '>=':op.ge, '<=':op.le, '=':op.eq, 
        'abs':     abs,
        'append':  op.add,  
        'apply':   apply,
        'begin':   lambda *x: x[-1],
        'car':     lambda x: x[0],
        'cdr':     lambda x: x[1:], 
        'cons':    lambda x,y: [x] + y,
        'eq?':     op.is_, 
        'equal?':  op.eq, 
        'length':  len, 
        'list':    lambda *x: list(x), 
        'list?':   lambda x: isinstance(x,list), 
        'map':     map,
        'max':     max,
        'min':     min,
        'not':     op.not_,
        'null?':   lambda x: x == [], 
        'number?': lambda x: isinstance(x, Number),   
        'procedure?': callable,
        'round':   round,
        'symbol?': lambda x: isinstance(x, Symbol),
    })
    return env

class Env(dict):
    "An environment: a dict of {'var':val} pairs, with an outer Env."
    def __init__(self, parms=(), args=(), outer=None):
        self.update(zip(parms, args))
        self.outer = outer
    def find(self, var):
        "Find the innermost Env where var appears."
        return self if (var in self) else self.outer.find(var)

global_env = standard_env()

################ Interaction: A REPL

def repl(prompt='lis.py> '):
    "A prompt-read-eval-print loop."
    while True:
        val = eval(parse(raw_input(prompt)))
        if val is not None: 
            print(lispstr(val))

def lispstr(exp):
    "Convert a Python object back into a Lisp-readable string."
    if isinstance(exp, List):
        return '(' + ' '.join(map(lispstr, exp)) + ')' 
    else:
        return str(exp)

################ Procedures

class Procedure(object):
    "A user-defined Scheme procedure."
    def __init__(self, parms, body, env):
        self.parms, self.body, self.env = parms, body, env
    def __call__(self, *args): 
        return eval(self.body, Env(self.parms, args, self.env))

################ eval

def eval(x, env=global_env):
    "Evaluate an expression in an environment."
    if isinstance(x, Symbol):      # variable reference
        return env.find(x)[x]
    elif not isinstance(x, List):  # constant literal
        return x                
    elif x[0] == 'quote':          # (quote exp)
        (_, exp) = x
        return exp
    elif x[0] == 'if':             # (if test conseq alt)
        (_, test, conseq, alt) = x
        exp = (conseq if eval(test, env) else alt)
        return eval(exp, env)
    elif x[0] == 'define':         # (define var exp)
        (_, var, exp) = x
        env[var] = eval(exp, env)
    elif x[0] == 'set!':           # (set! var exp)
        (_, var, exp) = x
        env.find(var)[var] = eval(exp, env)
    elif x[0] == 'lambda':         # (lambda (var...) body)
        (_, parms, body) = x
        return Procedure(parms, body, env)
    else:                          # (proc arg...)
        proc = eval(x[0], env)
        args = [eval(exp, env) for exp in x[1:]]
        return proc(*args)"""


novig_lispy_indented = """
        ################ Lispy: Scheme Interpreter in Python
        
        ## (c) Peter Norvig, 2010-16; See http://norvig.com/lispy.html
        
        from __future__ import division
        import math
        import operator as op
        
        ################ Types
        
        Symbol = str          # A Lisp Symbol is implemented as a Python str
        List   = list         # A Lisp List is implemented as a Python list
        Number = (int, float) # A Lisp Number is implemented as a Python int or float
        
        ################ Parsing: parse, tokenize, and read_from_tokens
        
        def parse(program):
            "Read a Scheme expression from a string."
            return read_from_tokens(tokenize(program))
        
        def tokenize(s):
            "Convert a string into a list of tokens."
            return s.replace('(',' ( ').replace(')',' ) ').split()
        
        def read_from_tokens(tokens):
            "Read an expression from a sequence of tokens."
            if len(tokens) == 0:
                raise SyntaxError('unexpected EOF while reading')
            token = tokens.pop(0)
            if '(' == token:
                L = []
                while tokens[0] != ')':
                    L.append(read_from_tokens(tokens))
                tokens.pop(0) # pop off ')'
                return L
            elif ')' == token:
                raise SyntaxError('unexpected )')
            else:
                return atom(token)
        
        def atom(token):
            "Numbers become numbers; every other token is a symbol."
            try: return int(token)
            except ValueError:
                try: return float(token)
                except ValueError:
                    return Symbol(token)
        
        ################ Environments
        
        def standard_env():
            "An environment with some Scheme standard procedures."
            env = Env()
            env.update(vars(math)) # sin, cos, sqrt, pi, ...
            env.update({
                '+':op.add, '-':op.sub, '*':op.mul, '/':op.truediv, 
                '>':op.gt, '<':op.lt, '>=':op.ge, '<=':op.le, '=':op.eq, 
                'abs':     abs,
                'append':  op.add,  
                'apply':   apply,
                'begin':   lambda *x: x[-1],
                'car':     lambda x: x[0],
                'cdr':     lambda x: x[1:], 
                'cons':    lambda x,y: [x] + y,
                'eq?':     op.is_, 
                'equal?':  op.eq, 
                'length':  len, 
                'list':    lambda *x: list(x), 
                'list?':   lambda x: isinstance(x,list), 
                'map':     map,
                'max':     max,
                'min':     min,
                'not':     op.not_,
                'null?':   lambda x: x == [], 
                'number?': lambda x: isinstance(x, Number),   
                'procedure?': callable,
                'round':   round,
                'symbol?': lambda x: isinstance(x, Symbol),
            })
            return env
        
        class Env(dict):
            "An environment: a dict of {'var':val} pairs, with an outer Env."
            def __init__(self, parms=(), args=(), outer=None):
                self.update(zip(parms, args))
                self.outer = outer
            def find(self, var):
                "Find the innermost Env where var appears."
                return self if (var in self) else self.outer.find(var)
        
        global_env = standard_env()
        
        ################ Interaction: A REPL
        
        def repl(prompt='lis.py> '):
            "A prompt-read-eval-print loop."
            while True:
                val = eval(parse(raw_input(prompt)))
                if val is not None: 
                    print(lispstr(val))
        
        def lispstr(exp):
            "Convert a Python object back into a Lisp-readable string."
            if isinstance(exp, List):
                return '(' + ' '.join(map(lispstr, exp)) + ')' 
            else:
                return str(exp)
        
        ################ Procedures
        
        class Procedure(object):
            "A user-defined Scheme procedure."
            def __init__(self, parms, body, env):
                self.parms, self.body, self.env = parms, body, env
            def __call__(self, *args): 
                return eval(self.body, Env(self.parms, args, self.env))
        
        ################ eval
        
        def eval(x, env=global_env):
            "Evaluate an expression in an environment."
            if isinstance(x, Symbol):      # variable reference
                return env.find(x)[x]
            elif not isinstance(x, List):  # constant literal
                return x                
            elif x[0] == 'quote':          # (quote exp)
                (_, exp) = x
                return exp
            elif x[0] == 'if':             # (if test conseq alt)
                (_, test, conseq, alt) = x
                exp = (conseq if eval(test, env) else alt)
                return eval(exp, env)
            elif x[0] == 'define':         # (define var exp)
                (_, var, exp) = x
                env[var] = eval(exp, env)
            elif x[0] == 'set!':           # (set! var exp)
                (_, var, exp) = x
                env.find(var)[var] = eval(exp, env)
            elif x[0] == 'lambda':         # (lambda (var...) body)
                (_, parms, body) = x
                return Procedure(parms, body, env)
            else:                          # (proc arg...)
                proc = eval(x[0], env)
                args = [eval(exp, env) for exp in x[1:]]
                return proc(*args)"""


@pytest.mark.parametrize("input, expected", [
    # NO-OP
    ("", ""),
    ("hello", "hello"),
    ("one\ntwo", "one\ntwo"),
    # strip prefix, one line
    ("   hello", "hello"),
    # strip prefix, two lines
    ("""
    hello
    dolly""", "hello\ndolly"),
    # deindent to initial line
    ("""
    hello
        dolly""", "hello\n    dolly"),
    # deindent to second line
    ("""
        hello
    dolly""", "    hello\ndolly"),
    (novig_lispy_indented, norvig_lispy_dedented)

])
def test_deindent(input, expected):
    actual = deindent_block(input)
    assert actual == expected, '{0} != {1}'.format(actual, expected)


ex_with_lead_in = """
    

    hello, world
        goodbye, world!"""


ex_with_lead_out_nl_same_indent = """
    hello, world
        goodbye, world!
    """


ex_with_lead_out_no_indent = """
    hello, world
        goodbye, world!
"""

ex_expected = """\
hello, world
    goodbye, world!"""


@pytest.mark.parametrize("case", [
    ex_with_lead_in,
    ex_with_lead_out_nl_same_indent,
    ex_with_lead_out_no_indent
])
def test_lead_in__lead_out(case):
    assert deindent_block(case) == ex_expected


# def test_deindent():
#     t1 = timeit.timeit("deindent_block(novig_lispy_indented)", globals=globals(), number=100000)
#
#     t2 = timeit.timeit("deindent_str_block(novig_lispy_indented)", globals=globals(), number=100000)
#     assert 0, f"ctext: {t1}\n text: {t2}"
