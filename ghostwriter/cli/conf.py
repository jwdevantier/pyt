from pathlib import Path
import yaml
import typing as t
from re import compile as re_compile
from multiprocessing import cpu_count
from os.path import expanduser
import io
import logging
from ghostwriter.utils import spec as s

log = logging.getLogger(__file__)

CONF_NAME = "ghostwriter.conf.yml"

GW_CONF_LOGGING_SPEC = s.keys({
    'level': s.opt(
        s.inseq(['debug', 'info', 'warning', 'error', 'critical']),
        'info'),
    'format': s.opt(s.str, '%(asctime)s - %(message)s'),
    'datefmt': s.opt(s.str, '%Y-%m-%d %H:%M:%S')
})


class GhostwriterConfigurationError(Exception):
    pass


def _natint(value):
    value = int(value)
    return value if value > 0 else False


def _nonempty(value):
    try:
        return value if len(value) != 0 else False
    except TypeError:
        return False


re_py_identifier = re_compile(r"(?:[a-zA-Z_][a-zA-Z_0-9]*)")


def _py_import_path(value):
    """
    Test if str could be a valid Python import path.

    Import paths are characterized by being str's with more than
    one component separated by periods ('.').
    Each component must be a valid package/module/function name and
    all identifiers accept a-zA-Z_ as their first character and
    a-zA-Z_0-9 for all subsequent characters.
    """
    if not isinstance(value, str):
        return False

    parts = value.split('.')
    if len(parts) <= 1:
        return False

    if all((len(value) > 0
            and re_py_identifier.match(value)
            for value in parts)):
        return value
    raise ValueError("invalid")


def pp_log_conf(config: t.Mapping[str, t.Any]):
    with io.StringIO() as sbuf:
        yaml.safe_dump(config, sbuf, default_flow_style=False, sort_keys=False)
        sbuf.flush()
        log.info("configuration used:\n" + '\n'.join([f"   {line}" for line in sbuf.getvalue().split('\n')]))


class Directory(s.SpecBase):
    """

    Conform resolves '.' to current working directory, '~' to the current user's
    home directory and relative paths are made absolute in relation to the
    current working directory.
    """

    @classmethod
    def __value(cls, value: t.Any) -> t.Optional[Path]:
        try:
            return Path(expanduser(value)).absolute()
        except TypeError:
            return None

    @classmethod
    def _valid(cls, value: t.Any):
        return cls._conform(value) is not s.Invalid

    @classmethod
    def _explain(cls, value: t.Any):
        path: t.Optional[Path] = cls.__value(value)
        if not path:
            return f"expected a path string, got '{type(value)}'"
        elif not path.exists():
            return f"directory '{path}' does not exist"
        elif not path.is_dir():
            return f"path '{path}' is not a directory"
        else:
            return None

    @classmethod
    def _conform(cls, value: t.Any):
        path: t.Optional[Path] = cls.__value(value)
        if path and path.is_dir():
            return path.as_posix()
        return s.Invalid

    @staticmethod
    def _name():
        return "Directory"


GW_CONF_PARSER_SPEC = s.keys({
    'open': s.opt(s.str, '<@@'),
    'close': s.opt(s.str, '@@>'),
    'processes': s.opt(s.predicate(_natint, 'positive int'), cpu_count()),
    'temp_file_suffix': s.opt(s.str, '.gw.tmp'),
    'include_patterns': s.req(s.seqof(s.str)),
    'ignore_patterns': s.opt(s.seqof(s.str), []),
    'ignore_dir_patterns': s.opt(s.seqof(s.str), []),
    'search_paths': s.req(s.allof({
        'non-empty?': s.predicate(_nonempty, 'non-empty?'),
        'list of dirs?': s.seqof(Directory())
    })),
    'post_process_fn': s.opt(s.allof({
        'string?': s.str,
        'python import path': s.predicate(_py_import_path, "python import path")
    })),
})

GW_CONF_SPEC = s.keys({
    'logging': GW_CONF_LOGGING_SPEC,
    'parser': GW_CONF_PARSER_SPEC,
})


# TODO: improve - in particular, the error formatting needs to show the data and
#       the error
class SpecError(GhostwriterConfigurationError):
    def __init__(self, spec: s.Spec, value: t.Any):
        self.spec = spec
        self.value = value
        self.errors = s.explain(spec, value)
        super().__init__(f"value failed to conform to spec: {self.errors}")

    def __repr__(self):
        return f"{type(self).__name__}<{self.errors}>"


class ConfLogging:
    def __init__(self, conf):
        if not s.valid(GW_CONF_LOGGING_SPEC, conf):
            raise SpecError(GW_CONF_LOGGING_SPEC, conf)
        self.level: str = conf['level']
        self.format: str = conf['format']
        self.datefmt: str = conf['datefmt']

    def __repr__(self):
        return (f"{type(self).__name__}<"
                f"level: {self.level}, format: {self.format}"
                f", datefmt: {self.datefmt}>")


class ConfParser:
    def __init__(self, conf):
        conf_c = s.conform(GW_CONF_PARSER_SPEC, conf)
        if conf_c == s.Invalid:
            raise RuntimeError("LOLCAEK")
        if not s.valid(GW_CONF_PARSER_SPEC, conf):
            raise SpecError(GW_CONF_PARSER_SPEC, conf)
        self.open = conf['open']
        self.close = conf['close']
        self.processes = conf['processes']
        self.temp_file_suffix = conf['temp_file_suffix']
        self.include_patterns = conf['include_patterns']
        self.ignore_patterns = conf['ignore_patterns']
        self.ignore_dir_patterns = conf['ignore_dir_patterns']
        self.search_paths = conf['search_paths']
        self.post_process_fn = conf['post_process_fn']

    def __repr__(self):
        return (f"{type(self).__name__}<"
                f"open: {self.open}, close: {self.close}, "
                f"processes: {self.processes}, "
                f"include_patterns: {self.include_patterns}, "
                f"ignore_patterns: {self.ignore_patterns}, "
                f"ignore_dir_patterns: {self.ignore_dir_patterns}, "
                f"search_paths: {self.search_paths}"
                ">")


class Configuration:
    def __init__(self, project: Path, conf: dict):
        if not s.valid(GW_CONF_SPEC, conf):
            raise SpecError(GW_CONF_SPEC, conf)
        self.project: Path = project
        self.logging = ConfLogging(conf['logging'])
        self.parser = ConfParser(conf['parser'])

    def __repr__(self):
        return (
            f"{type(self).__name__}<"
            f"logging: {self.logging}"
            f", parser: {self.parser}"
            ">")


class ConfigurationNotFoundError(GhostwriterConfigurationError):
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        super().__init__(f"Could not find '{CONF_NAME}' in '{project_dir}'")


class ConfigurationFileInvalidError(SpecError):
    pass


def load(project: Path):
    conf_path = project.joinpath(CONF_NAME)
    try:
        with open(str(conf_path), 'r') as f:
            config = yaml.safe_load(f)
        if not s.valid(GW_CONF_SPEC, config):
            raise ConfigurationFileInvalidError(GW_CONF_SPEC, config)
    except FileNotFoundError as e:
        raise ConfigurationNotFoundError(project) from e
    # except PermissionError
    config_c = s.conform(GW_CONF_SPEC, config)
    if config_c == s.Invalid:
        # Should never happen here - we already validated the spec
        ConfigurationFileInvalidError(GW_CONF_SPEC, config)

    pp_log_conf(config_c)
    return Configuration(project, config_c)
