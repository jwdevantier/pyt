from ghostwriter.utils.cogen.component import Component
from ghostwriter.utils.cogen.interpreter cimport Writer, interpret
from ghostwriter.utils.cogen.parser cimport CogenParser, Program
from ghostwriter.utils.cogen.tokenizer cimport Tokenizer


cdef Program prog = CogenParser(Tokenizer("""\
% r __main__
% /r""".lstrip())).parse_program()


cdef class ComponentSnippet(SnippetCallbackFn):
    def __init__(self, component: Component, dict blocks = None):
        if not isinstance(component, Component):
            raise ValueError(f"component must be of instance component, got: '{type(component)}'")
        self.component = component
        self.blocks = blocks or {}

    cpdef void apply(self, Context ctx, str snippet, str prefix, IWriter fw) except *:
        # TODO: could I use 'body' instead of '__main__' to avoid polluting scope?
        interpret(prog, Writer(fw), {}, {'__main__': self.component})
