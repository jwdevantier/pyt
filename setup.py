from setuptools import find_packages
from Cython.Build import cythonize
from distutils.core import setup
from distutils.extension import Extension
import pathlib as pl
import os
import subprocess
import traceback
import sys
import distutils.cmd

import re

req_line_rgx = re.compile(r'^-r\s+(?P<fname>.+)$')


def this_dir() -> pl.Path:
    return pl.Path(__file__).parent


def requirements_from(fname):
    def resolv_require_line(req):
        match = req_line_rgx.match(req)
        if match:
            return requirements_from(match.group('fname'))
        return req

    with open(fname) as req_file:
        req_line_iter = (line.strip() for line in req_file)
        requirements = [
            requirement for requirement in req_line_iter
            if requirement and not requirement.startswith('#')
        ]

        def reqlist():
            for req in requirements:
                resolved_req = resolv_require_line(req)
                if isinstance(resolved_req, list):
                    for elem in resolved_req:
                        yield elem
                else:
                    yield resolved_req

        return reqlist()


install_requires = list(requirements_from('requirements.txt'))
test_requires = list(requirements_from('requirements.dev.txt'))

HIDDEN_MODULES = [
    'ghostwriter.writer',
    'ghostwriter.utils.template',
]


class BuildBinaryCommand(distutils.cmd.Command):
    """
    """
    description = "build self-contained binary"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        """
        Generate self-contained binary file
        """
        program_main_file = os.path.join(this_dir().as_posix(), 'ghostwriter', '__main__.py')
        if not pl.Path(program_main_file).exists():
            print("ERROR!")
            print("    pyinstaller command needs a 'main' file - some file which starts the program.")
            print(f"    The build script references: '{program_main_file}'")
            print(f"but this file cannot be found!")
            sys.exit(1)
        cmd = ["pyinstaller", "--noconfirm", '--nowindow', '--onefile']
        for module in HIDDEN_MODULES:
            cmd.extend(['--hidden-import', module])
        cmd.extend(['--name', 'gwrite', program_main_file])
        print("> ", " ".join(cmd))
        subprocess.check_call(cmd)


setup(
    name='ghostwriter',
    version='0.1',
    packages=find_packages(),
    license='MIT',
    long_description=open('README.md').read(),
    entry_points={
        'console_scripts': [
            'gwrite = ghostwriter.__main__:cli'
        ]
    },
    install_requires=install_requires,
    test_suite='tests',
    tests_require=test_requires,
    # Cython Modules
    ext_modules=cythonize([
        Extension("ghostwriter.parser.fileparser", [
            "ghostwriter/parser/fileparser.pyx",
            "ghostwriter/parser/wcsenc.c"]),
        Extension("ghostwriter.utils.spec.spec", ["ghostwriter/utils/spec/spec.pyx"]),
        Extension("ghostwriter.utils.fhash.fhash", ["ghostwriter/utils/fhash/fhash.pyx"]),
        Extension("ghostwriter.utils.template.tokens", ["ghostwriter/utils/template/tokens.pyx"]),
        Extension("ghostwriter.utils.cogen.tokenizer", ["ghostwriter/utils/cogen/tokenizer.pyx"]),
        Extension("ghostwriter.utils.cogen.pratt", ["ghostwriter/utils/cogen/pratt.pyx"]),
        Extension("ghostwriter.utils.cogen.parser", ["ghostwriter/utils/cogen/parser.pyx"]),
    ], annotate=True),
    cmdclass={
        'build_bin': BuildBinaryCommand
    }

)
