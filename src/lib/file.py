"""File system library."""

import os


def is_binary(file_path: str, block_size: int = 4096) -> bool:
    """Check if `file_path` is binary.

    Parameters
    ----------
    file_path : str
        Path to the file to analyze.
    block_size : int
        Chunk to read

    Returns
    -------
    bool
        `True` if binary else `False`

    """
    # https://stackoverflow.com/a/7392391
    textchars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F})

    with open(file_path, "rb") as f:
        return bool(f.read(block_size).translate(None, textchars))


def get_md5(file_path: str, chunksize: int = 1024 * 1024) -> str:
    """Generate MD5 hash for a file.

    Parameters
    ----------
    file_path : str
        Path to the file to generate MD5 hash.
    chunksize : int
        Chunk size to read

    Returns
    -------
    str
        MD5 hash.

    """
    from hashlib import md5

    m = md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunksize):
            m.update(chunk)

    return m.hexdigest()


def get_blake3(file_path: str, chunksize: int = 1024 * 1024) -> str:
    """Generate blake3 hash for a file.

    Parameters
    ----------
    file_path : str
        Path to the file to generate MD5 hash.
    chunksize : int
        Chunk size to read

    Returns
    -------
    str
        blake3 hash.

    """
    from blake3 import blake3

    m = blake3()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunksize):
            m.update(chunk)

    return m.hexdigest()


def get_content(file_path: str) -> list[str] | None:
    """Read text file as list of lines with UTF-8 encoding.

    Parameters
    ----------
    file_path : str
        Path to the file to extract content.

    Returns
    -------
    list[str] | None
        Content of the file.

    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.readlines()
    except OSError:
        return None


def find_file_in_dirs(file_path: str, dirs_path: list[str]) -> str | None:
    """Find which directory among `dirs_path` contains `file_path`.

    Parameters
    ----------
    file_path : str
        Path to the file to find in `dirs_path`
    dirs_path : list[str]
        List of directories where to search for `file_path`

    Returns
    -------
    str | None
        Returns the directory, else returns `None`

    """
    for dir_path in dirs_path:
        rel_path = os.path.relpath(file_path, dir_path)
        if not rel_path.startswith(".."):
            return dir_path

    return None
