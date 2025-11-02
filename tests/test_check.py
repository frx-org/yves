"""Test lib/check.py."""


def test_command_exists():
    """Test `command_exists`."""
    from lib.check import command_exists

    assert command_exists("pytest")
    assert not command_exists("cmd_not_exist")


def test_check_config(tmp_path):
    """Test `check_config` if it correctly checks configuration file values."""
    from uuid import uuid4

    from lib.cfg import default_config, write_config
    from lib.check import check_config

    abs_path = tmp_path / f"{uuid4().hex}"
    default_cfg = default_config()
    write_config(default_cfg, abs_path)
    assert check_config(abs_path)

    abs_path = tmp_path / f"{uuid4().hex}"
    default_cfg = default_config()
    default_cfg["filesystem"]["min_lines_changed"] = "-1"
    write_config(default_cfg, abs_path)
    assert not check_config(abs_path)

    abs_path = tmp_path / f"{uuid4().hex}"
    default_cfg = default_config()
    default_cfg["filesystem"]["similarity_threshold"] = "1"
    write_config(default_cfg, abs_path)
    assert check_config(abs_path)

    abs_path = tmp_path / f"{uuid4().hex}"
    default_cfg = default_config()
    default_cfg["filesystem"]["similarity_threshold"] = "0"
    write_config(default_cfg, abs_path)
    assert check_config(abs_path)

    abs_path = tmp_path / f"{uuid4().hex}"
    default_cfg = default_config()
    default_cfg["filesystem"]["similarity_threshold"] = "-0.01"
    write_config(default_cfg, abs_path)
    assert not check_config(abs_path)

    abs_path = tmp_path / f"{uuid4().hex}"
    default_cfg = default_config()
    default_cfg["filesystem"]["similarity_threshold"] = "1.2"
    write_config(default_cfg, abs_path)
    assert not check_config(abs_path)
