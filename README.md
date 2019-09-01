
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
