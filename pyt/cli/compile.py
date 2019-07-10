import logging
import os
import sys

import typing as t
import multiprocessing as mp
from multiprocessing import Process

import watchgod
from watchgod.watcher import Change

from pyt.parser import Parser, Context, PARSE_OK, parse_result_err
import pyt.parser as pparse
from pyt.utils.decorators import Debounce
from pyt.protocols import IWriter
from pyt.utils.fhash import file_hash
from pyt.utils.watch import Watcher, CompileWatcher, MPScheduler
from pyt.cli.conf import Configuration, ConfParser

log = logging.getLogger(__name__)

CompileFn = t.Callable[[], None]
Changeset = t.Set[t.Tuple[Change, str]]


def dirwalker(w: Watcher, path: str) -> t.Iterator[os.DirEntry]:
    for entry in os.scandir(path):
        if entry.is_dir():
            if w.should_watch_dir(entry):
                yield from dirwalker(w, entry.path)
        elif w.should_watch_file(entry):
            yield entry


def expand_snippet(ctx: Context, snippet: str, prefix: str, out: IWriter):
    out.write(f"{prefix}look out!\n")
    out.write(f"{prefix}something more")


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
        parser = Parser(
            self.parser_conf.open, self.parser_conf.close,
            temp_file_suffix=self.parser_conf.temp_file_suffix,
            should_replace_file=self.should_replace)
        # TODO: expand sys.path
        fpath: str = jobs.recv()
        while fpath != "<stop>":
            log.info(f"received fpath '{fpath}' (type: {type(fpath)})")
            out = parser.parse(expand_snippet, fpath)
            fpath = jobs.recv()
            if out:
                log.error(f"parse() => {out} ({pparse.parse_result_err(out)})")
                log.error(f"in: {fpath}")


def do_compile_singlecore(parser: ConfParser, walker: CompileWatcher, should_replace: t.Callable[[str, str], bool]):
    parser = Parser(
        parser.open, parser.close,
        temp_file_suffix=parser.temp_file_suffix,
        should_replace_file=should_replace)  # TODO: wrong - should provide fdb too
    # TODO: expand-snippet, expand sys.path
    for entry in dirwalker(walker, walker.root_path):
        out = parser.parse(expand_snippet, entry.path)
        if out != 0:
            log.error(f"parse() => {out} ({pparse.parse_result_err(out)})")
            log.error(f"in: {entry.path}")


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
            p = Process(target=do_compile_singlecore, args=(config.parser, walker, should_replace))
            p.start()
            p.join()

        compilefn = compile_sc
    else:
        log.info(f"MP compile mode selected ({config.parser.processes} processes)")
        sched = MPCompiler(config.parser, should_replace=should_replace)

        def compile_mp():
            nonlocal walker, sched
            with sched as s:
                s.submit((entry.path for entry in dirwalker(walker, root_path)))

        compilefn = compile_mp

    compilefn()
    if not watch:
        sys.exit(0)

    compile = Debounce(compilefn)
    for changes in watchgod.watch(
            config.project.absolute().as_posix(),
            watcher_cls=CompileWatcher,
            watcher_kwargs={'config': config}):
        real_changes = list(fdb.sync(changes))
        if real_changes:
            print("REAL CHANGES")
            print(real_changes)
            compile.schedule()
