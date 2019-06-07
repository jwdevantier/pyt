from setuptools import find_packages
from Cython.Build import cythonize
from distutils.core import setup
from distutils.extension import Extension

import re

req_line_rgx = re.compile(r'^-r\s+(?P<fname>.+)$')


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

setup(
    name='pyt',
    version='0.1',
    packages=find_packages(),
    license='MIT',
    long_description=open('README.md').read(),
    entry_points={
        'console_scripts': [
            'pyt = pyt.__main__:cli'
        ]
    },
    install_requires=install_requires,
    test_suite='tests',
    tests_require=test_requires,
    # Cython Modules
    ext_modules=cythonize([
        Extension("pyt.parser.fileparser", ["pyt/parser/fileparser.pyx"]),
        Extension("pyt.utils.spec.spec", ["pyt/utils/spec/spec.pyx"])
    ], annotate=True)

)
