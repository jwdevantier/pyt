
## Setup Ghostwriter

```
# create python virtual environment (venv)
python3 -m venv venv

# use venv
source venv/bin/activate

# compile Cython modules
(venv) python setup.py build_ext --inplace

# install ghostwriter in venv
# (from within the same directory as 'setup.py')
pip install -e .
```

## Setup docs project
The documentation project is in the `docs` directory. To initialise it:

```
cd docs

# setup venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# start mkdocs server
cd gwdocs
mkdocs serve
```

## Profiling
For profiling, [pyinstrument](https://github.com/joerick/pyinstrument) and [cprofile](https://docs.python.org/3.7/library/profile.html)
are the standard. cprofile is a c-powered variant of `profile`, and both are included in the Python distribution.
Pyinstrument, however, is available as a Python package.

Pyinstrument is arguably more user-friendly, the following will profile the application and produce a HTML page which
allows you to drill down into where the program spent its time:
```
pyinstrument -r html $HOME/repos/personal/pyt/ghostwriter/__main__.py compile
```

However, for Cython code, `pyinstrument` will not work, Therefore, cProfile is a better choice in this case.

### Gotchas
* In Cython, special instructions must be added to the file to enable profiling
    * These changes incur an overhead, remove when done
* Profiling will not work across processes
    * Can run the profiler on the entire program or on a section of code.
    * Profiling a section of code and saving results to disk is a way of profiling the worker processes.

Resources
* [Cython Profiling Tutorial](https://cython.readthedocs.io/en/latest/src/tutorial/profiling_tutorial.html)
* [Profiling in Python (overview)](https://medium.com/@antoniomdk1/hpc-with-python-part-1-profiling-1dda4d172cdf)

### Profiling in Cython - summary
In the file to be profiled, add:

```
# cython: profile=True
```

**NOTE**: The above must be added to every module taking part in the code
you wish to profile. Failure to do so will mean details stop at whichever
top-level function called within that module.

```
from ghostwriter.utils.profile import profiler


with profiler(f"/tmp/{worker_id}"):
   # ... do some work
```