from tempfile import NamedTemporaryFile
from os import replace as os_replace, remove as os_remove
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

    template = """
    parser:
        open: '<<self.open>>'
        close: '<<self.close>>'
        processes: <<int(self.procs)>>
        temp_file_suffix: '.gw.tmp'

        # include_patterns, ignore_patterns and ignore_dir_patterns all use
        # Python regex syntax - use pythex.org to experiment.
        include_patterns:
          - '.*\.js$'
          - '.*\.php$'
          - '.*\.s?css$'
        ignore_patterns:
          - '^Makefile$'
        ignore_dir_patterns:
          - '.*/node_modules$'
          - '.*/\.git$'
          - '.*/\.virtualenv$'
          - '.*/venv$'
          - '.*/[^/]+\.egg-info$'
          
        # These directories will hold Python packages (directories) and
        # modules (files). These directories are where your project's snippets,
        # components and so on should be placed.
        #
        # 
        # Given a function 'myfun' in 'snippets/foo/bar.py', it can be called
        #from a snippet by writing 'foo.bar.myfun'.
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


# TODO: write to buffer first, that way, we avoid halfway filled out files
# TODO: validate or reject..(?)
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
