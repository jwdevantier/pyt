import glob
import sys
import os
import typing as t
from Cython.Build import cythonize
from distutils.core import setup

SRC_ROOT = 'pyt'

def find_files(rgx: str) -> t.List[str]:
    return glob.glob(
        os.path.join(sys.path[0], f'{SRC_ROOT}/', '**/', rgx), recursive=True)

setup(
    ext_modules=cythonize(find_files('*.pyx'), annotate=True)
)