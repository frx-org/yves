"""Test lib/file.py."""


def test_is_binary(tmp_path):
    """Test `is_binary`."""
    from lib.file import is_binary

    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("")
    assert not is_binary(str(empty_file))

    text_file = tmp_path / "non_binary.txt"
    text_file.write_text("Hello, I am Yves.")
    assert not is_binary(str(text_file))

    binary_file = tmp_path / "example.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03\x04")
    assert is_binary(str(binary_file))


def test_get_md5(tmp_path):
    """Test `get_md5`."""
    from lib.file import get_md5

    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("")
    assert get_md5(empty_file) == "d41d8cd98f00b204e9800998ecf8427e"

    text_file = tmp_path / "text.txt"
    text_file.write_text("Hello, I am Yves.")
    assert get_md5(text_file) == "e38574aba81f17d0c6842f5b4fde525c"

    binary_file = tmp_path / "example.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03\x04")
    assert get_md5(binary_file) == "d05374dc381d9b52806446a71c8e79b1"


def test_find_file_in_dirs(tmp_path):
    """Test `find_file_in_dirs`."""
    from random import choice
    from uuid import uuid4

    from lib.file import find_file_in_dirs

    dirs_path = [tmp_path / f"{uuid4().hex}" for _ in range(10)]
    parent_dir = choice(dirs_path)
    abs_path = parent_dir / "find_me_please.txt"
    non_existent_dirs_path = [tmp_path / f"{uuid4().hex}" for _ in range(10)]

    assert find_file_in_dirs(abs_path, dirs_path) == parent_dir
    assert find_file_in_dirs(abs_path, non_existent_dirs_path) is None
