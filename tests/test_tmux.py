"""Test lib/tmux.py."""


def test_is_valid_command():
    """Test `is_valid_command`."""
    from lib.tmux import is_valid_command

    assert not is_valid_command("")
    assert not is_valid_command("this Is a v3ry long Command so this IS IN VA LID")
    assert is_valid_command("this Is an acceptable Command hence we Should Keep it")
