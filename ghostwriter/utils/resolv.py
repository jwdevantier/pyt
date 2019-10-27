import typing as t
import logging
from importlib import import_module
from re import compile as re_compile

log = logging.getLogger(__name__)


class ResolvError(Exception):
    MESSAGE = "Error looking up identifier"

    def __init__(self, fqn: str, message: t.Optional[str] = None):
        """
        Parameters
        ----------
        fqn : str
            Fully-qualified name of the attribute to load
        message : str
            The error message
        """
        self.fqn = fqn
        self.message = message or self.MESSAGE
        super().__init__(f"{self.message} ({self.fqn})")


class InvalidLookupPath(ResolvError):
    MESSAGE = "Invalid lookup path"


class UnqualifiedPath(InvalidLookupPath):
    MESSAGE = "unqualified path (no '.' encountered in lookup path)"


class ParentModuleNotFound(ResolvError):
    def __init__(self, mod_path: str, missing: str, fqn: str):
        super().__init__(
            fqn,
            f"error during lookup of {fqn}, module {missing} not found")
        self.module_path = mod_path
        self.missing_module = missing


class DependencyModuleNotFound(ResolvError):
    def __init__(self, mod_path: str, missing: str, fqn: str):
        super().__init__(
            fqn,
            f"error during import of '{mod_path}', attempted to import module '{missing}' which could not be found")
        self.module_path = mod_path
        self.missing_module = missing


class AttrNotFound(ResolvError):
    def __init__(self, mod_path: str, attr: str):
        super().__init__(
            '.'.join([mod_path, attr]),
            f"No attribute '{attr}' found in module at '{mod_path}'")


def parse_fqn_identifier(fqn_ident: str) -> t.Tuple[str, str]:
    parts = fqn_ident.strip().split('.')
    if len(parts) == 1:
        raise UnqualifiedPath(fqn_ident)
    else:
        return '.'.join(parts[:-1]), parts[-1]


module_not_found_rgx = re_compile(r"No module named '(?P<module>[a-zA-Z_]\w*)'")


def resolv(fqn_attr: str) -> t.Any:
    """
    Resolves fully qualified path to some attribute to the attribute itself
    Parameters
    ----------
    fqn_attr : str
        A string formatted as a fully qualified path to some attribute.
        E.g. `one.two.three.four` where `one` and `two` are packages,
        `three` is a module and `four` is the attribute itself.
    Returns
    -------
        The resolved attribute
    """
    log.debug(f"resolving fqn attr '{fqn_attr}'")
    mod_path, attr = parse_fqn_identifier(fqn_attr)
    log.debug(f"expanding {fqn_attr} (attr: {attr}, module: {mod_path})")
    try:
        mod = import_module(mod_path)
    except ModuleNotFoundError as e:
        match = module_not_found_rgx.match(str(e))
        if not match:
            raise RuntimeError("Program error: failed to parse error from ModuleNotFoundError") from e
        missing_module = match['module']
        if missing_module in mod_path.split('.'):
            print(f"mod_path '{mod_path}', missing: '{missing_module}', attr: '{attr}'")
            raise ParentModuleNotFound(mod_path, missing_module, attr) from e
        # some other dependency failed
        raise DependencyModuleNotFound(mod_path, missing_module, attr) from e

    try:
        return getattr(mod, attr)
    except AttributeError as e:
        raise AttrNotFound(mod_path, attr) from e


def resolv_opt(val: t.Optional[str], default=None):
    return resolv(val) if val else default
