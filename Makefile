
# 'make' will list all documented targets, see https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
.DEFAULT_GOAL := help
.PHONY: help
help:
	@echo "\033[33mAvailable targets, for more information, see \033[36mREADME.md\033[0m"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


.PHONY: clean
clean: clean-py clean-build clean-cython ## clean all temporary files
	# this file must exist to disambiguate different test files with
	# the same basename (i.e. filename)
	touch tests/__init__.py

.PHONY: clean-build
clean-build: ## remove build files, build/ (wheel) and dist/ (pyinstaller)
	rm -rf dist build

.PHONY: clean-py
clean-py: ## remove all pyc and __pycache__ files - sometimes needed when refactoring tests
	find tests -name '*.pyc' -delete
	find tests -name "__pycache__" -delete

	find ghostwriter -name '*.pyc' -delete
	find ghostwriter -name '__pycache__' -delete

.PHONY: clean-cython
clean-cython:
	find ghostwriter -name '*\.cpython-*.so' -delete

.PHONY: _venv
_venv:
	test -d venv || python3 -m venv venv ;\
		. venv/bin/activate ;\
		pip install -Ur requirements.txt

.PHONY: venv
venv: ## create virtualenv (in 'venv') if needed
	test -d venv || make _venv

.PHONY: venv-dev
venv-dev: venv ## install development requirements
	. venv/bin/activate ;\
		pip install -Ur requirements.dev.txt

.PHONY: compile
compile: venv ## compile Cython & C code
	. venv/bin/activate ;\
		python setup.py build_ext --inplace

.PHONY: dev-setup
dev-setup: venv-dev compile ## install package in editable mode (console scripts defined in setup.py are available)
	. venv/bin/activate ;\
		pip install -e .

.PHONY: test
test: venv compile ## run test suite
	. venv/bin/activate ;\
		pytest .

.PHONY: package-binary
package-binary: venv-dev ## build a binary (wheel) distribution package
	. venv/bin/activate ;\
		python setup.py bdist_wheel

.PHONY: package-source
package-source: venv-dev ## create a source distribution package
	. venv/bin/activate ;\
		python setup.py sdist

.PHONY: bin
bin: venv-dev ## build self-contained binary in dist/
	. venv/bin/activate ;\
		pyinstaller \
			--noconfirm \
			--nowindow \
			--onefile \
			--name gwriter \
			--additional-hooks-dir=pyinstaller-hooks \
			ghostwriter/__main__.py
