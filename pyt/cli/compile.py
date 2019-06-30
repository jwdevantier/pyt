import logging
import os
from re import compile as re_compile
from watchdog.events import (FileModifiedEvent, FileMovedEvent, FileDeletedEvent)
import typing as t

from pyt.utils import watch
from pyt.parser import Parser, Context, PARSE_OK, parse_result_err
import pyt.parser as pparse
from pyt.protocols import IWriter
from pyt.utils.fhash import file_hash
from pyt.cli.conf import Configuration

log = logging.getLogger(__name__)


# TODO: - scandir works, templating invoked .nothing is written to supposed output file


def _file_map(fn: t.Callable, path: str, regex_match: t.Callable):
    for entry in os.scandir(path):
        if entry.is_dir():
            yield from _file_map(fn, entry.path, regex_match)
        elif regex_match(entry.path):
            log.debug(f"match: '{entry.path}'")
            yield fn(entry)


def file_map(fn: t.Callable, path: str, include_patterns: t.List[str]):
    valid_file = re_compile('|'.join(f'(?:{entry})' for entry in include_patterns)).match
    return _file_map(fn, path, valid_file)


def expand_snippet(ctx: Context, snippet: str, prefix: str, out: IWriter):
    out.write(f"{prefix}look out!\n")
    out.write(f"{prefix}something more")


# TODO: new file created and populated, on_created only or ALSO on_modified?
#       (hypothesis - only listen for on_modified, on_deleted and on_moved to know all)
class CompileWatcher(watch.Watcher):
    def __init__(self, config: Configuration, fmap: t.Dict[str, str]):
        super().__init__(config)
        self._parser = Parser(self.conf.parser.open, self.conf.parser.close)
        self._file_hashes = fmap

    def on_modified(self, event: FileModifiedEvent):
        old_hash = self._file_hashes.get(event.src_path, '')
        new_hash = file_hash(event.src_path)
        if old_hash == new_hash:
            return

        parse_res = self._parser.parse(expand_snippet, event.src_path, None)
        if parse_res != PARSE_OK:
            log.error(f"Parsing of '{event.src_path}' failed: {parse_result_err(parse_res)}")
            return
        self._file_hashes[event.src_path] = file_hash(event.src_path)

    def on_moved(self, event: FileMovedEvent):
        # Do we care ? The file shouldn't necessarily have changed
        if event.src_path not in self._file_hashes:
            return
        self._file_hashes[event.dest_path] = self._file_hashes[event.src_path]
        self._file_hashes.pop(event.src_path, None)

    def on_deleted(self, event: FileDeletedEvent):
        self._file_hashes.pop(event.src_path, None)


def compile_once(config: Configuration) -> None:
    parser = Parser(config.parser.open, config.parser.close)
    fid = 0

    def parse_file(entry: os.DirEntry):
        nonlocal fid
        fid += 1
        out_path = f'/tmp/parse-result.{fid}'
        out = parser.parse(expand_snippet, entry.path, None)
        if out != 0:
            print(f"parse() => {out} ({pparse.parse_result_err(out)})")
            print(f"in:  {entry.path}")
            print(f"out: {out_path}")
        else:
            log.debug(f"parse() => {out} {file_hash(out_path)}")

    log.info(f"compile path '{config.project.absolute().as_posix()}'")
    list(file_map(parse_file, config.project.absolute().as_posix(), config.parser.include_patterns))
    print(f"parsed {fid} files.")


def compile_watch(config: Configuration):
    w = CompileWatcher(config, {})
    w()


def compile(config: Configuration, watch: bool) -> None:
    log.info(f"compile mode: '{'watch' if watch else 'once'}'")
    # TODO: re-enable the compile-once step
    compile_once(config)
    if watch:
        compile_watch(config)
