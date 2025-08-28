import os


def is_binary(file_path: str) -> bool:
    """Check if `file_path` is binary by attemptint to decode as UTF-8.

    Parameters
    ----------
    file_path : str
        Path to the file to analyze.

    Returns
    -------
    bool
        `True` if binary else `False`

    """

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for _ in f:
                continue
        return False
    except (OSError, UnicodeDecodeError):
        return True


def get_md5(file_path: str) -> str:
    """Generate MD5 hash for a file.

    Parameters
    ----------
    file_path : str
        Path to the file to generate MD5 hash.

    Returns
    -------
    str
        MD5 hash.

    """

    from hashlib import md5

    with open(file_path, "rb") as f:
        content = f.read()
        return md5(content).hexdigest()


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
    """Find which directory among `dirs_path` contains `file_path`

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
