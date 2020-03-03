from tempfile import NamedTemporaryFile
from os import replace as os_replace, remove as os_remove, mkdir as os_mkdir
from pathlib import Path
import sys
from multiprocessing import cpu_count
import click as c
import colorama as clr
from ghostwriter.cli.cliutils import *
from ghostwriter.utils.iwriter import IWriter
from ghostwriter.utils.cogen import Component
from ghostwriter.utils.cogen.parser import CogenParser
from ghostwriter.utils.cogen.tokenizer import Tokenizer
from ghostwriter.utils.cogen.interpreter import Writer, interpret
from ghostwriter.utils.ctext import deindent_block


class ConfDefault(Component):
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    procs = 5
    open = "<@@"
    close = "@@>"
    search_paths = ["snippets"]
    include_patterns = []
    ignore_patterns = []
    ignore_dir_patterns = []

    template = """
    parser:
        open: '<<self.open>>'
        close: '<<self.close>>'
        processes: <<int(self.procs)>>
        temp_file_suffix: '.gw.tmp'
        
        # include_patterns, ignore_patterns and ignore_dir_patterns all use
        # Python regex syntax - use pythex.org to experiment.
        include_patterns:
        % for include_pattern in self.include_patterns
          - '<<include_pattern>>'
        % /for
        
        # ignore_patterns can be used to ignore files which would
        # otherwise be included in the compile because of the include_patterns
        % if self.ignore_patterns
        ignore_patterns:
        % for ignore_pattern in self.ignore_patterns
          - '<<ignore_pattern>>'
        % /for
        % else
        # ignore_patterns:
        #   - '*\.md$'
        % /if
        
        # ignore_dir_patterns can be used to ignore entire directories
        # (and thus all files inside them). Use this to reduce the number of
        # files visited during compilation.
        % if self.ignore_dir_patterns
        ignore_dir_patterns:
        % for ignore_dir_pattern in self.ignore_dir_patterns
          - '<<ignore_dir_pattern>>'
        % /for
        % else
        # ignore_dir_patterns:
        #   - '.*/\.git$'
        #   - '.*/node_modules$'
        % /if
        
        # These directories will hold Python packages (directories) and
        # modules (files). These directories are where your project's snippets,
        # components and so on should be placed.
        search_paths:
        % for search_path in self.search_paths
          - "<<search_path>>"
        % /for
    
    logging:
        # The logging error determines the detail and amount of output shown.
        # Levels: debug, info, warning, error
        level: info
        format: '%(asctime)s - %(message)s'
        datefmt: '%Y-%m-%d %H:%M:%S'"""


TEMPLATES = {
    "python": {
        "description": "typical python project",
        "component": ConfDefault,
        "options": {
            "include_patterns": [
                r".*\.pyx?$",
                r".*\.pxd$"
            ],
            "ignore_patterns": [
                r".*\.pyc$",
            ],
            "ignore_dir_patterns": [
                r".*/\.git$",
                r"python\d\.\d$",
                r"__pycache__$",
                r".*/[^/]+\.egg-info$",
            ]
        }
    }
}


class BufferedFileWriter(IWriter):
    """
    Implements an all-or-nothing* semantic for writing a file.
    (Should prevent half-written files)
    """
    def __init__(self, fpath):
        super().__init__()
        self.fpath = fpath
        self.fd = NamedTemporaryFile(mode="w", delete=False)

    def __enter__(self):
        self.fd = open(self.fpath, 'w')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fd.close()
        if not exc_type:
            os_replace(self.fd.name, self.fpath)
        else:
            os_remove(self.fd.name)

    def write(self, contents):
        self.fd.write(contents)


def _render_template(template: Component, scope: dict, writer: IWriter):
    scope["__main__"] = template
    program = """\
    % r __main__
    % /r"""
    parser = CogenParser(Tokenizer(deindent_block(program)))
    interpret(parser.parse_program(), Writer(writer), {}, scope)


def write_configuration(template: Component, scope: dict, fpath: str):
    with BufferedFileWriter(fpath) as fw:
        _render_template(template, scope, fw)


B_BLU = f"{clr.Style.BRIGHT}{clr.Fore.BLUE}"
B_MAG = f"{clr.Style.BRIGHT}{clr.Fore.MAGENTA}"
B_YEL = f"{clr.Style.BRIGHT}{clr.Fore.YELLOW}"
CLR = clr.Style.RESET_ALL


def _prompt(txt, confirm=True, **kwargs):
    prompt_txt = f"{clr.Style.BRIGHT}{clr.Fore.GREEN}?{clr.Style.RESET_ALL} {clr.Style.BRIGHT}{txt}{clr.Style.RESET_ALL}"
    while True:
        result = c.prompt(prompt_txt, **kwargs)
        if not confirm or kwargs.get("default", None) == result:
            break
        confirm_txt = f"Confirm {B_YEL}{result}{CLR}?"
        if c.confirm(confirm_txt, default=False, abort=False, prompt_suffix=': ', show_default=True, err=False):
            break
    return result


def validate_or_retry(validator, prompt_fn, *args, **kwargs):
    result = prompt_fn(*args, **kwargs)
    error = validator(result)
    while error:
        echo_err(error)
        result = prompt_fn(*args, **kwargs)
        error = validator(result)
    return result


def validate_searchpaths(search_paths):
    sps = [sp.strip() for sp in search_paths.split(",")]
    for sp in sps:
        path = Path(sp)
        if path.exists() and not path.is_dir():
            return f"'{sp}' exists, but is not a directory!"
    return


def _header(txt):
    c.echo(f"\n\n{B_YEL}>>{CLR} {B_BLU}{txt}{CLR}")


def cli_init(conf_path: Path):
    options = {}
    _header("Snippet Tags")
    c.echo(deindent_block(f"""
    When parsing files. Ghostwriter will look for snippets, places to insert generated output,
    by looking for lines containing both the special opening- and closing tag sequences.
    
    By default, these are {B_BLU}<@@{CLR} and {B_BLU}@@>{CLR}, meaning '{B_BLU}<@@{CLR} {B_YEL}hello.awesome.world {B_BLU}@@>{CLR}'
    would be the opening line for '{B_YEL}hello.awesome.world{CLR}' and everything until
    '{B_BLU}<@@ /{B_YEL}hello.awesome.world {B_BLU}@@>{CLR}' is replaced by the generated output."""))

    c.echo("\n")
    options["open"] = _prompt("snippet open tag", default="<@@", type=str)
    options["close"] = _prompt("snippet close tag", default="@@>", type=str)

    _header("Search Paths")
    c.echo(deindent_block(f"""
    When looking for snippets such as '{B_YEL}hello.awesome.world{CLR}', Ghostwriter will start
    its search in a series of directories known as `search paths`.
    
    In case of '{B_YEL}hello.awesome.world{CLR}', Ghostwriter would expect to find the function
    {B_YEL}world{CLR} inside {B_YEL}hello/awesome.py{CLR}, where the {B_YEL}hello{CLR} directory is found inside one
    of the search path directories."""))

    c.echo("\n")
    options["search_paths"] = [
        sp.strip() for sp in validate_or_retry(
            validate_searchpaths, _prompt,
            "search paths (separate with commas)", default="snippets").split(",")]

    _header("Processes (Concurrency)")
    c.echo(deindent_block("""
    Ghostwriter will use one or more processes to speed up compilation."""))

    c.echo("\n")
    options["procs"] = _prompt("number of processes", default=max(1, int(cpu_count()/2)), type=int)

    _header("Templates")
    c.echo(deindent_block(f"""
    Templates tweak the configuration file's patterns determining what files to include
    or exclude and which directories to skip searching entirely.
    
    These patterns are meant as a quick-start, by all means tweak them to your project."""))

    c.echo("\n")
    template = TEMPLATES[_prompt("select template", default="python", type=c.Choice(TEMPLATES.keys()))]

    # Done collecting data
    for search_path in options["search_paths"]:
        abs_search_path = Path(".", search_path)
        try:
            os_mkdir(abs_search_path.name)
        except FileExistsError:
            if not abs_search_path.is_dir():
                echo_err(f"Error initializing - '{search_path}' exists but is not a directory")
                sys.exit(1)

    options = {
        **template["options"],
        **options
    }
    write_configuration(template["component"](**options), {}, conf_path.name)
