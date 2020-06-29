from functools import wraps
from os import path
import inspect
from ghostwriter.utils.cogen.parser import CogenParser, Program
from ghostwriter.utils.cogen.tokenizer import Tokenizer
from ghostwriter.utils.decorators import CachedStaticProperty
from ghostwriter.utils.ctext import deindent_block


class ComponentMeta(type):
    def __new__(mcs, clsname, bases, clsdict):
        if '__init__' in clsdict:
            orig_init = clsdict['__init__']
        else:
            def orig_init(self, *args, **kwargs):
                pass

        @wraps(orig_init)
        def __ghostwriter_component_init__(self, *args, **kwargs):
            """
            Compute scope for component before invoking normal init.
            """
            # Fast exit: only run component initialization once per type
            #
            # Because of the metaclass, this init method will always be the the outermost __init__ method run.
            # Remember, this init wrapper is installed on _EACH_ init method along the inheritance chain, from the
            # class inheriting from Component and onward.
            #
            # To avoid running this logic for each component initialized (and for each __init__ in the subclasses(s) of
            # component), we install an attribute on the type itself which, if found, skips initialization logic and
            # calls the wrapped __init__ method directly.
            if getattr(type(self), "__ghostwriter_component_initialized__", False):
                orig_init(self, *args, **kwargs)
                return
            setattr(type(self), "__ghostwriter_component_initialized__", True)

            # compute scope
            setattr(type(self), '__ghostwriter_component_scope__', {
                ident: obj
                for ident, obj
                in inspect.getmembers(inspect.getmodule(self))
                if (inspect.ismodule(obj)
                    or getattr(obj, '__ghostwriter_component__', False))})
            # call actual init function
            orig_init(self, *args, **kwargs)

        clsdict['__init__'] = __ghostwriter_component_init__
        typ = super().__new__(mcs, clsname, bases, clsdict)
        return typ


class Component(metaclass=ComponentMeta):
    """
    The basic template component interface.

    This class defines the interface to implement for new components.
    Note that parsing components is moved to an external function in order
    to avoid accidentally overriding this logic.
    """
    # Important to set here - cannot infer which types are components
    # in metaclass code otherwise (timing issue, attr may not yet have been set)
    __ghostwriter_component__ = True
    # Will be overwritten by one-time init function
    __ghostwriter_component_scope__ = {}

    # TODO: this is wrong, it should be a class property, otherwise the static class property below will fail
    @property
    def template(self) -> str:
        """
        Return the DSL content defining the component.

        Returns
        -------
            A string containing the DSL template making up this component.
        """
        raise NotImplementedError("'template() -> str' method not implemented")

    @CachedStaticProperty
    def ast(cls) -> Program:
        """Parse Component program text into AST

        Lazily parses the component program text into an AST and caches it for future use."""
        program = CogenParser(Tokenizer(deindent_block(cls.template))).parse_program()
        program.file_path = path.abspath(inspect.getfile(cls))
        program.component = cls.__name__
        return program
