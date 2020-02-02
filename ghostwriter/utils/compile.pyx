import logging
import sys
from time import time
from typing import Tuple, Iterator, Set
from multiprocessing import Process
from os import scandir
from multiprocessing.connection import Connection
from watchgod.watcher import Change
import colorama as clr
from ghostwriter.utils.fhash cimport file_hash
from ghostwriter.utils.cwatch cimport AllWatcher, CompileWatcher, SearchPathsWatcher, MPScheduler
from ghostwriter.cli.conf import Configuration, ConfParser
from ghostwriter.parser.fileparser cimport Context, Parser, GhostwriterSnippetError, SnippetCallbackFn
from ghostwriter.parser import parse_result_err
from ghostwriter.utils.resolv import resolv, resolv_opt
from ghostwriter.utils.iwriter cimport IWriter
from ghostwriter.utils.watch import watch_dirs, WatcherConfig
from ghostwriter.parser.fileparser cimport ShouldReplaceFileAlways
from ghostwriter.utils.decorators import Debounce


log = logging.getLogger(__name__)
Changeset = Set[Tuple[Change, str]]


cdef class FileSyncReplace(ShouldReplaceFileCallbackFn):
    def __init__(self, FileChecksums filecheck):
        self.filecheck = filecheck

    cpdef bint apply(self, str temp, str orig) except *:
        return self.filecheck.should_replace(temp, orig)


cdef class FileChecksums:
    def __init__(self):
        self.fmap = {}

    cpdef bint should_replace(self, str temp, str orig):
        new_hash = file_hash(temp)
        if orig not in self.fmap:
            orig_hash = file_hash(orig)
            self.fmap[orig] = orig_hash
        else:
            orig_hash = self.fmap[orig]
        # replace file iff. contents have changed from the parsing
        return orig_hash != new_hash

    def sync(self, changeset: Changeset) -> Iterator[Tuple[Change, str]]:
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
        cdef dict fmap = self.fmap
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


cdef class SnippetError(Exception):
    def __init__(self, str snippet_fqn: str, str message: str):
        """

        Parameters
        ----------
        snippet_fqn : str
            Fully-qualified name of snippet, e.g. `foo.bar.baz.mysnippet`
        message : str
            The exception error message
        """
        cdef list parts = snippet_fqn.strip().split('.')
        if len(parts) == 1:
            self.module = "<none>"
            self.fn_name = <str>parts[0]
        else:
            self.module = <str>".".join(parts[:-1])
            self.fn_name = <str>parts[-1]

        self.message = message
        super().__init__(self.message)


cdef class SnippetFunctionSignatureError(SnippetError):
    def __init__(self, snippet_fqn: str):
        super().__init__(
            snippet_fqn,
            f"incorrect snippet function signature, must be: '<snippet name>(ctx: Context, prefix: str, out: Writer)'")


cdef class SnippetUnhandledExceptionError(SnippetError):
    def __init__(self, snippet_fqn: str):
        super().__init__(
            snippet_fqn,
            f"Unhandled exception")


cdef void print_snippet_error(e: GhostwriterSnippetError) except *:
    """
    Print formatted error message, summarizing the details leading to a snippet expansion error.
    Parameters
    ----------
    e : GhostwriterSnippetError

    Returns
    -------
        None
    """
    cdef SnippetError cause
    if not isinstance(e.cause, SnippetError):
        log.info(f"unhandled error (type: {type(e).__name__} while parsing snippet")
        raise e

    cause = e.cause
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


cdef class ExpandSnippet(SnippetCallbackFn):
    cpdef void apply(self, Context ctx, str snippet, str prefix, IWriter fw) except *:
        cdef object snippet_fn = resolv(snippet)  # LOADS of possible exceptions
        cdef str fn_name
        try:
            snippet_fn(ctx, prefix, fw)
        except TypeError as e:
            fn_name = snippet.split('.')[-1]
            if str(e).startswith(f"{fn_name}()"):
                raise SnippetFunctionSignatureError(snippet) from e
            else:
                raise SnippetUnhandledExceptionError(snippet) from e
        except Exception as e:
            raise SnippetUnhandledExceptionError(snippet) from e


cdef class CompileFileCallbackFn:
    cpdef void parse_file(self, str fpath) except *:
        pass


cpdef compile_files(AllWatcher w, CompileFileCallbackFn compiler, path: str):
    for entry in scandir(path):
        if entry.is_dir():
            if w.should_watch_dir(entry):
                compile_files(w, compiler, entry.path)
        elif w.should_watch_file(entry):
            compiler.parse_file(entry.path)


cdef class SCCompileFileCallbackFn(CompileFileCallbackFn):
    cdef:
        Parser parser
        SnippetCallbackFn on_snippet
        int num_calls

    def __init__(self, Parser parser, SnippetCallbackFn on_snippet):
        self.parser = parser
        self.on_snippet = on_snippet
        self.num_calls = 0

    cpdef void parse_file(self, str fpath) except *:
        try:
            out = self.parser.parse(self.on_snippet, fpath)
            if out:
                log.error(f"parse() => {out} ({parse_result_err(out)})")
                log.error(f"in: {fpath}")
            self.num_calls += 1
        except GhostwriterSnippetError as e:
            print_snippet_error(e)
        except Exception as e:
            log.exception("parsing - unhandled exception caught:")


cdef void do_compile_singlecore(parser_conf: ConfParser, CompileWatcher walker,
                          ShouldReplaceFileCallbackFn should_replace) except *:
    cdef:
        Parser parser = Parser(
            f"/tmp/.ghostwriter-w0-{parser_conf.temp_file_suffix}",
            parser_conf.open, parser_conf.close,
            should_replace_file=should_replace,
            post_process=resolv_opt(parser_conf.post_process_fn))
        ExpandSnippet expand_snippet = ExpandSnippet()
        SCCompileFileCallbackFn compile_file = SCCompileFileCallbackFn(parser, expand_snippet)
    sys.path.extend(parser_conf.search_paths)
    compile_files(walker, compile_file, walker.root_path)
    log.info(f"parsed {compile_file.num_calls} files during compile pass")


cdef class CompileCallbackFn:
    cpdef void apply(self) except *:
        pass


cdef class SingleCoreCompileFn(CompileCallbackFn):
    cdef:
        object parser_conf
        CompileWatcher watcher
        ShouldReplaceFileCallbackFn should_replace

    def __init__(self, parser_conf: ConfParser, CompileWatcher watcher, ShouldReplaceFileCallbackFn should_replace):
        self.parser_conf = parser_conf
        self.watcher = watcher
        self.should_replace = should_replace

    cpdef void apply(self) except *:
        t_start = time()
        p = Process(target=do_compile_singlecore, args=(self.parser_conf, self.watcher, self.should_replace))
        p.start()
        p.join()
        log.info("compile finished in {0:.2f}s".format(time() - t_start))


cdef class MPCompiler(MPScheduler):
    cdef:
        object parser_conf
        ShouldReplaceFileCallbackFn should_replace

    def __init__(self,
                 parser_conf: ConfParser,
                 ShouldReplaceFileCallbackFn should_replace):
        self.parser_conf = parser_conf
        self.should_replace = should_replace
        super().__init__(parser_conf.processes)

    cpdef void _target(self, str worker_id, object jobs: Connection):
        cdef:
            Parser parser
            str fpath
            ExpandSnippet expand_snippet = ExpandSnippet()
        sys.path.extend(self.parser_conf.search_paths)
        parser = Parser(
            f"/tmp/.ghostwriter-w{worker_id}-{self.parser_conf.temp_file_suffix}",
            self.parser_conf.open, self.parser_conf.close,
            should_replace_file=self.should_replace,
            post_process=resolv_opt(self.parser_conf.post_process_fn))
        fpath = jobs.recv()
        # with profiler(f"/tmp/{worker_id}"):
        while fpath != "<stop>":
            try:
                out = parser.parse(expand_snippet, fpath)
                if out:
                    log.error(f"parse() => {out} ({parse_result_err(out)})")
                    log.error(f"in: {fpath}")
            except GhostwriterSnippetError as e:
                print_snippet_error(e)
            except Exception as e:
                log.exception("parsing - unhandled exception caught:")
            fpath = jobs.recv()


cdef class MPCompileFileCallbackFn(CompileFileCallbackFn):
    cdef MPCompiler compiler
    cdef public int num_calls

    def __init__(self, MPCompiler compiler):
        self.compiler = compiler

    cpdef void parse_file(self, str fpath) except *:
        self.num_calls += 1
        self.compiler.submit_one(fpath)


cdef class MultiCoreCompileFn(CompileCallbackFn):
    cdef:
        MPCompiler compiler
        CompileWatcher watcher
        CompileFileCallbackFn compile_file

    def __init__(self, object parser_conf, CompileWatcher watcher, ShouldReplaceFileCallbackFn should_replace):
        self.compiler = MPCompiler(parser_conf, should_replace=should_replace)
        self.watcher = watcher
        self.compile_file = MPCompileFileCallbackFn(self.compiler)

    cpdef void apply(self) except *:
        t_start = time()
        self.compile_file.num_calls = 0  # reset counter
        with self.compiler as compiler:
            compile_files(self.watcher, self.compile_file, self.watcher.root_path)
        log.info("compile pass: {0} jobs in {1:.2f}s".format(self.compile_file.num_calls, time() - t_start))


cpdef void cli_compile(config: Configuration, bint watch):
    cdef:
        str root_path = config.project.absolute().as_posix()
        CompileWatcher watcher = CompileWatcher(root_path, config=config)
        FileChecksums fdb
        ShouldReplaceFileCallbackFn should_replace
        CompileCallbackFn compiler

    if watch:
        fdb = FileChecksums()
        should_replace = FileSyncReplace(fdb)
    else:
        should_replace = ShouldReplaceFileAlways()

    if config.parser.processes == 1:
        log.info("Single-core compile mode selected (change config.parser.processes to enable MP)")
        compiler = SingleCoreCompileFn(config.parser, watcher, should_replace)
    else:
        log.info(f"MP compile mode selected ({config.parser.processes} processes)")
        compiler = MultiCoreCompileFn(config.parser, watcher, should_replace)

    compiler.apply()

    if not watch:
        sys.exit(0)

    compile = Debounce(compiler.apply)
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