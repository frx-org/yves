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


def test_get_blake3(tmp_path):
    """Test `get_blake3`."""
    from lib.file import get_blake3

    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("")
    assert (
        get_blake3(empty_file)
        == "af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262"
    )

    text_file = tmp_path / "text.txt"
    text_file.write_text("Hello, I am Yves.")
    assert (
        get_blake3(text_file)
        == "05461be1cdd26fa8a3b3b4d1ef03fea9e34254279f8ef7f2db1e8cc458ca9ae0"
    )

    binary_file = tmp_path / "example.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03\x04")
    assert (
        get_blake3(binary_file)
        == "b40b44dfd97e7a84a996a91af8b85188c66c126940ba7aad2e7ae6b385402aa2"
    )


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
