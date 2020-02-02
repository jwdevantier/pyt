from os.path import dirname as os_path_dirname
from os.path import basename as os_path_basename
import tempfile


def tmp_file_path(path: str, suffix: str) -> str:
    """ Get path to a temporary file

    Parameters
    ----------
    path
    suffix

    Returns
    -------
        Path to some otherwise unused file.
    """
    in_dir = os_path_dirname(path)
    fname = f"{os_path_basename(path)}."

    tf = tempfile.NamedTemporaryFile(
        dir=in_dir, prefix=fname, suffix=suffix, delete=False)
    fname = tf.name
    tf.close()
    return fname