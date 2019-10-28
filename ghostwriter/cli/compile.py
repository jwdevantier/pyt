import logging
import os
import sys

import typing as t
import multiprocessing as mp
from multiprocessing import Process
from importlib import import_module
from time import time

from watchgod.watcher import Change
import colorama as clr

from ghostwriter.parser import Parser, Context, PARSE_OK, parse_result_err, GhostwriterSnippetError
import ghostwriter.parser as pparse
from ghostwriter.utils.decorators import Debounce
from ghostwriter.protocols import IWriter
from ghostwriter.utils.fhash import file_hash

from ghostwriter.utils.watch import Watcher, SearchPathsWatcher, CompileWatcher, MPScheduler, watch_dirs, WatcherConfig
from ghostwriter.cli.conf import Configuration, ConfParser
from ghostwriter.utils.resolv import resolv, resolv_opt

log = logging.getLogger(__name__)

CompileFn = t.Callable[[], None]
Changeset = t.Set[t.Tuple[Change, str]]


def compiler_input_files(w: Watcher, path: str) -> t.Iterator[os.DirEntry]:
    for entry in os.scandir(path):
        if entry.is_dir():
            if w.should_watch_dir(entry):
                yield from compiler_input_files(w, entry.path)
        elif w.should_watch_file(entry):
            yield entry


def parse_snippet_name(snippet_fqn: str) -> t.Tuple[str, str]:
    parts = snippet_fqn.strip().split('.')
    if len(parts) == 1:
        return "<none>", parts[0]
    else:
        return '.'.join(parts[:-1]), parts[-1]


class SnippetError(Exception):
    def __init__(self, snippet_fqn: str, message: str):
        """

        Parameters
        ----------
        snippet_fqn : str
            Fully-qualified name of snippet, e.g. `foo.bar.baz.mysnippet`
        message : str
            The exception error message
        """
        self.module, self.fn_name = parse_snippet_name(snippet_fqn)

        self.message = message
        super().__init__(self.message)


class SnippetFunctionSignatureError(SnippetError):
    def __init__(self, snippet_fqn: str):
        super().__init__(
            snippet_fqn,
            f"incorrect snippet function signature, must be: '<snippet name>(ctx: Context, prefix: str, out: Writer)'")


class SnippetUnhandledExceptionError(SnippetError):
    def __init__(self, snippet_fqn: str):
        super().__init__(
            snippet_fqn,
            f"Unhandled exception")


def expand_snippet(ctx: Context, snippet: str, prefix: str, out: IWriter):
    snippet_fn = resolv(snippet)  # LOADS of possible exceptions
    try:
        snippet_fn(ctx, prefix, out)
    except TypeError as e:
        fn_name = snippet.split('.')[-1]
        if str(e).startswith(f"{fn_name}()"):
            raise SnippetFunctionSignatureError(snippet) from e
        else:
            raise SnippetUnhandledExceptionError(snippet) from e
    except Exception as e:
        raise SnippetUnhandledExceptionError(snippet) from e


class FileChecksums:
    def __init__(self):
        self.fmap: t.Dict[str, str] = {}

    def should_replace(self, temp: str, orig: str) -> bool:
        new_hash = file_hash(temp)
        if orig not in self.fmap:
            orig_hash = file_hash(orig)
            self.fmap[orig] = orig_hash
        else:
            orig_hash = self.fmap[orig]
        # replace file iff. contents have changed from the parsing
        return orig_hash != new_hash

    def sync(self, changeset: Changeset) -> t.Iterator[t.Tuple[Change, str]]:
        """Lazily synchronizes file checksums based on incoming changeset

        Parameters
        ----------
        changeset : Changeset
            Changes detected by the file system watcher represented as a set
            of 2-tuples of change-type (added, modified, deleted) and the file
            path.

        Returns
        -------
            Iterator for sync operation. Genuine changes (where files are
            modified) are returned.
        """
        fmap = self.fmap
        for typ, fpath in changeset:
            if typ == Change.modified:
                new_hash = file_hash(fpath)
                old_hash = fmap.get(fpath, None)
                if new_hash != old_hash:
                    fmap[fpath] = new_hash
                    yield typ, fpath
            elif typ == Change.added:
                fmap[fpath] = file_hash(fpath)
                yield typ, fpath
            elif typ == Change.deleted:
                fmap.pop(fpath, None)


def print_snippet_error(e: GhostwriterSnippetError) -> None:
    """
    Print formatted error message, summarizing the details leading to a snippet expansion error.
    Parameters
    ----------
    e : GhostwriterSnippetError

    Returns
    -------
        None
    """
    if not isinstance(e.cause, SnippetError):
        log.info(f"unhandled error (type: {type(e).__name__} while parsing snippet")
        raise e

    cause: SnippetError = e.cause
    if cause.__cause__ and isinstance(cause, SnippetUnhandledExceptionError):
        error = str(cause.__cause__)
    else:
        error = cause.message
    log.info(f"""\
{clr.Style.BRIGHT}{clr.Fore.RED}Error parsing snippet {clr.Fore.MAGENTA}{cause.module}.{cause.fn_name}{clr.Fore.RED}:{clr.Style.RESET_ALL}
\t{clr.Fore.MAGENTA}{clr.Style.BRIGHT}Used at:{clr.Style.RESET_ALL} {e.file} (ending at line: {e.line_num})
\t{clr.Fore.MAGENTA}{clr.Style.BRIGHT}Snippet:{clr.Style.RESET_ALL} from {cause.module} import {cause.fn_name}
\t{clr.Fore.MAGENTA}{clr.Style.BRIGHT}Reason:{clr.Style.RESET_ALL}  {error}
""")


class MPCompiler(MPScheduler):
    def __init__(self,
                 parser_conf: ConfParser,
                 should_replace: t.Callable[[str, str], bool] = lambda tmp, orig: True):
        self.parser_conf = parser_conf
        self.should_replace = should_replace
        super().__init__()

    def _num_processes(self):
        return self.parser_conf.processes

    def _target(self, jobs: mp.connection.Connection):
        sys.path.extend(self.parser_conf.search_paths)
        parser = Parser(
            self.parser_conf.open, self.parser_conf.close,
            temp_file_suffix=self.parser_conf.temp_file_suffix,
            should_replace_file=self.should_replace,
            post_process=resolv_opt(self.parser_conf.post_process_fn))
        fpath: str = jobs.recv()
        while fpath != "<stop>":
            try:
                log.error("PRE PARSE")
                out = parser.parse(expand_snippet, fpath)
                log.error(f"parser.parse => {out}")
                if out:
                    log.error(f"parse() => {out} ({pparse.parse_result_err(out)})")
                    log.error(f"in: {fpath}")
            except GhostwriterSnippetError as e:
                print_snippet_error(e)
            except Exception as e:
                log.exception("parsing - unhandled exception caught:")
            fpath = jobs.recv()


def do_compile_singlecore(parser_conf: ConfParser, walker: CompileWatcher,
                          should_replace: t.Callable[[str, str], bool]):
    sys.path.extend(parser_conf.search_paths)
    parser = Parser(
        parser_conf.open, parser_conf.close,
        temp_file_suffix=parser_conf.temp_file_suffix,
        should_replace_file=should_replace,
        post_process=resolv_opt(parser_conf.post_process_fn))
    num_files_parsed = 0
    for entry in compiler_input_files(walker, walker.root_path):
        try:
            out = parser.parse(expand_snippet, entry.path)
            num_files_parsed += 1
            if out != 0:
                log.error(f"parse() => {out} ({pparse.parse_result_err(out)})")
                log.error(f"in: {entry.path}")
        except GhostwriterSnippetError as e:
            print_snippet_error(e)
    log.info(f"parsed {num_files_parsed} files during compile pass")


def should_always_replace(tmp: str, orig: str):
    """Strategy for determining if temporary file should overwrite the original

    Used by the parser when parsing files in 'in-place' mode, where a temporary
    file is created and at the end, the parser needs to determine if the result
    should overwrite the original.
    In some cases, such as when file contents are identical, you do not want
    to overwrite the file (and cause another change event to be processed in
    watch-mode)."""
    return True


# TODO: (enhance) single-shot compiling should not make fdb but should just overwrite files
def compile(config: Configuration, watch: bool) -> None:
    root_path = config.project.absolute().as_posix()
    walker = CompileWatcher(root_path, config=config)
    fdb: t.Optional[FileChecksums] = None
    if watch:
        fdb = FileChecksums()
    should_replace: t.Callable[[str, str], bool] = fdb.should_replace if fdb else should_always_replace

    if config.parser.processes == 1:
        log.info("Single-core compile mode selected (change config.parser.processes to enable MP)")

        def compile_sc():
            nonlocal config, walker
            t_start = time()
            p = Process(target=do_compile_singlecore, args=(config.parser, walker, should_replace))
            p.start()
            p.join()
            log.info("compile finished in {0:.2f}s".format(time() - t_start))

        compilefn = compile_sc
    else:
        log.info(f"MP compile mode selected ({config.parser.processes} processes)")
        sched = MPCompiler(config.parser, should_replace=should_replace)

        def compile_mp():
            nonlocal walker, sched
            t_start = time()
            with sched as s:
                njobs = s.submit((entry.path for entry in compiler_input_files(walker, root_path)))
            log.info("compile pass: {0} jobs in {1:.2f}s".format(njobs, time() - t_start))

        compilefn = compile_mp

    compilefn()
    if not watch:
        sys.exit(0)
    else:
        # Should be unnecessary, only to appease MyPy
        fdb = fdb or FileChecksums()

    compile = Debounce(compilefn)
    dirs_to_watch = [WatcherConfig('search_path', path, SearchPathsWatcher) for path in config.parser.search_paths]
    dirs_to_watch.append(
        WatcherConfig('project', config.project.absolute().as_posix(), CompileWatcher, {'config': config}))

    for tag, changes in watch_dirs(dirs_to_watch):
        if tag == 'search_path':
            compile.schedule()
        else:
            real_changes = list(fdb.sync(changes))
            if real_changes:
                compile.schedule()
