import typing as t
from functools import wraps
from ghostwriter.utils.iwriter cimport IWriter
from ghostwriter.utils.cogen.component import Component
from ghostwriter.utils.cogen.parser cimport CogenParser
from ghostwriter.utils.cogen.tokenizer cimport Tokenizer
from ghostwriter.utils.cogen.interpreter cimport Writer, interpret
from ghostwriter.utils.error cimport WrappedException, ExceptionInfo, catch_exception_info

# TODO: tests - had an indentation error in this code.


class SnippetEvalException(WrappedException):
    def __init__(self, ExceptionInfo ei):
        # remove the outermost stack frame which will point to this file. We only wrap the
        # exception to present a nicer format to the error logger in `fileparser.pyx`.
        # Hence, the frame pointing to here is not necessary.
        ei.stacktrace.pop(0)
        super().__init__(ei)


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
                raise SnippetEvalException(catch_exception_info()) from e

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