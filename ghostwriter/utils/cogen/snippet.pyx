import typing as t
from functools import wraps
from ghostwriter.utils.iwriter cimport IWriter
from ghostwriter.utils.cogen.component import Component
from ghostwriter.utils.cogen.parser cimport CogenParser
from ghostwriter.utils.cogen.tokenizer cimport Tokenizer
from ghostwriter.utils.cogen.interpreter cimport Writer, interpret


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
            cdef object main_component = fn()  # type: Component
            if not isinstance(main_component, Component):
                raise ValueError(f"snippet must return a Component instance, got '{type(main_component)}'")
            scope = {'__main__': main_component}
            program = """\
            % r __main__
            % /r"""
            parser = CogenParser(Tokenizer(program))
            writer = Writer(file_writer)
            interpret(parser.parse_program(), writer, blocks or {}, scope)

        return decorator

    return wrapper