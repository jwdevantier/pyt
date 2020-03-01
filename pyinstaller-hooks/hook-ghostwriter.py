# ghostwriter hook
#
# Pyinstaller is unable to pick up on most imports now. Presumably because the majority
# of imports are triggered after a separate thread is spawned.
#
# This hook computes imports by assuming that:
# * Every pxd/py file in ghostwriter should be included
# * Every dependency listed in requirements.txt should be included

from os import scandir, path
from itertools import chain


req_map = {
    "pyyaml": "yaml"
}


def requirements_imports():
  with open("requirements.txt") as reqs:
    for line in reqs:
      pkg = line.split("=")[0].lower()
      override = req_map.get(pkg)
      if override:
        yield override
      else:
        yield pkg.replace("-", "_")


def scantree(path):
  """Recursively yield DirEntry objects for given directory."""
  for entry in scandir(path):
    if entry.is_dir(follow_symlinks=False):
      yield from scantree(entry.path)  # see below for Python 2.x
    else:
      yield entry


def produce_imports(dirpath):
  def fmt_as_import(entry):
    dir = path.dirname(entry.path).replace(path.sep, ".")
    modname = path.splitext(path.basename(entry))[0]
    return ".".join([dir, modname])

  for entry in scantree(dirpath):
    if entry.path.endswith("pxd"):
      yield fmt_as_import(entry)
    elif entry.path.endswith(".py") and not entry.name in ("__init__.py", "__main__.py"):
      yield fmt_as_import(entry)


hiddenimports = [
  elem for elem
  in chain(requirements_imports(), produce_imports("ghostwriter"))
]
