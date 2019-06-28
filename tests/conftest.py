import pytest
from tempfile import NamedTemporaryFile
import os


@pytest.fixture
def tmpfile():
    file_handles = []
    REMOVE_FILES = False  # TODO: true when no longer debugging, this will litter the HDD

    def _tmpfile(*args, **kwargs):
        """
        Generate and open temporary file using ``io.open``

        ```
        with io.open(filename, 'w', encoding='utf8') as f:
            f.write(text)
        ```

        Parameters
        ----------
        args : list
            arguments to ``io.open``
        kwargs : dict
            keyword arguments to ``oi.open``

        Returns
        -------
            The open file  handle
        """
        with NamedTemporaryFile(prefix='test_parser', suffix='.tmp', delete=False) as tmp:
            fpath = tmp.name
        fh = open(fpath, *args, **kwargs)
        file_handles.append(fh)
        return fh

    try:
        yield _tmpfile
    finally:

        for fh in file_handles:
            file_path = fh.name
            try:
                fh.close()
            except:
                pass
            try:
                os.remove(file_path) if REMOVE_FILES else '<noop>'
            except:
                pass
