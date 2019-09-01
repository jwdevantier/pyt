
# Quick setup

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