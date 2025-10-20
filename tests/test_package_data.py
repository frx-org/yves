"""Test package-data directories."""


def test_prompts_dir():
    """Test if `yves.prompts` directory exist."""
    from importlib.resources import files

    assert files("yves.prompts").is_dir()


def test_check_dir():
    """Test if `yves.check` directory exist."""
    from importlib.resources import files

    assert files("yves.check").is_dir()
