
.PHONY: clean
clean:
	find tests -name '*.pyc' -delete
	find tests -name "__pycache__" -delete
	
	find ghostwriter -name '*.pyc' -delete
	find ghostwriter -name '__pycache__' -delete
	
	# this file must exist to disambiguate different test files with
	# the same basename (i.e. filename)
	touch tests/__init__.py

.PHONY: _venv
_venv:
	test -d venv || python3 -m venv venv ;\
		. venv/bin/activate ;\
		pip install -Ur requirements.txt

.PHONY: venv
venv:
	test -d venv || make _venv

.PHONY: venv-dev
venv-dev: venv
	. venv/bin/activate ;\
		pip install -Ur requirements.dev.txt

.PHONY: compile
compile: venv
	. venv/bin/activate ;\
		python setup.py build_ext --inplace

.PHONY: dev-setup
dev-setup: venv venv-dev compile
	. venv/bin/activate ;\
		pip install -e .
