import typing as t
from functools import wraps
import traceback
import sys
from ghostwriter.utils.iwriter cimport IWriter
from ghostwriter.utils.cogen.component import Component
from ghostwriter.utils.cogen.parser cimport CogenParser
from ghostwriter.utils.cogen.tokenizer cimport Tokenizer
from ghostwriter.utils.cogen.interpreter cimport Writer, interpret

# TODO: tests - had an indentation error in this code.


cdef class SnippetEvalException(Exception):
    """Wrap raised exception and format it for subsequent display.

    Wraps exception and implement methods expected by the error logger in `fileparser.pyx`.
    By rendering the stacktrace as-is we avoid showing additional stack frames pertaining to the
    internals of Ghostwriter."""

    def __init__(self):
        # NOTE: this exception expects to be created INSIDE an exception block
        cls, inst, tb = sys.exc_info()
        self._error = f"{cls.__qualname__}: {str(inst)}"
        super().__init__(self._error)
        tb_lines = traceback.format_tb(tb)
        # This accomplishes two things:
        # 1) strips the first string from tb_lines which corresponds to the outermost
        #    stack frame (from snippet.pyx itself)
        #    (Desirable as the user should only see the part of the stacktrace relevant to the his error)
        # 2) Writes the string which is shown when an exceptions stack trace is being printed.
        tb_lines[0] = f"Traceback (most recent call last):\n"
        self._error_details = "".join(tb_lines)

    cpdef str error_details(self):
        return self._error_details

    cpdef str error(self):
        return self._error


def snippet(dict blocks: t.Optional[dict] = None):
    """
    Create snippet from Component instance.

    Convenience decorator - wrap a function which takes a Scope instance and
    which returns a Component instance.

    Parameters
    ----------
    blocks:
        (Optional) additional blocks to use in DSL.

    Example
    -------
    @snippet()
    def my_snippet():
        foo = 'foo string'
        identity = lambda x: x
        return MyComponent(foo, identity)

    Returns
    -------
        A snippet function
    """

    def wrapper(fn: t.Callable[[], Component]):
        @wraps(fn)
        def decorator(_, prefix: str, file_writer: IWriter):
            # TODO: prefix would be the initial, base prefix...? Seems bad to ignore
            cdef object main_component
            try:
                main_component = fn()  # type: Component
            except Exception as e:
                # error messages already handling their own formatting are let through
                if hasattr(e, "error_details"):
                    raise e

                # wrap exception in a custom exception whose error_details attribute ensures only the
                # relevant parts of the stack trace are printed to the user.
                raise SnippetEvalException() from e

            if not isinstance(main_component, Component):
                # TODO: improve this - error stack trace should not show ghostwriter internals
                raise ValueError(f"snippet must return a Component instance, got '{type(main_component)}'")
            scope = {'__main__': main_component}
            program = f"""{prefix}% r __main__\n{prefix}% /r"""
            parser = CogenParser(Tokenizer(program))
            writer = Writer(file_writer)
            interpret(parser.parse_program(), writer, blocks or {}, scope)

        return decorator

    return wrapper