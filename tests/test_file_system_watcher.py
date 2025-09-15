"""Test lib/file_system_watcher.py."""


def test_update_from_config(tmp_path):
    """Test `update_from_config` if it updates the current `FileSystemWatcher` instance."""
    import os
    from configparser import ConfigParser
    from uuid import uuid4

    from lib.file_system_watcher import FileSystemWatcher, update_from_config

    abs_path = tmp_path / f"{uuid4().hex}"
    summarize_output_dir = tmp_path / "summarize_dir"
    default_watcher = FileSystemWatcher()
    watcher = FileSystemWatcher()

    config = ConfigParser()
    config["filesystem"] = {
        "enable": "false",
        "dirs": "~, . ,/home/me",
        "output_file": "new_output_file.json",
        "include_filetypes": ".py ,.nix,.nu",
        "exclude_filetypes": ".o",
        "major_changes_only": "True",
        "min_lines_changed": "6",
        "similarity_threshold": "0.4",
    }
    config["tmux"] = {
        "output_file": "tmux_output_file.json",
    }
    config["summarizer"] = {
        "output_dir": summarize_output_dir,
    }
    with open(abs_path, "w") as f:
        config.write(f)

    update_from_config(watcher, abs_path)
    assert default_watcher != watcher
    assert watcher == FileSystemWatcher(
        False,
        [os.path.expanduser("~"), ".", "/home/me"],
        "new_output_file.json",
        "tmux_output_file.json",
        str(summarize_output_dir),
        [".py", ".nix", ".nu"],
        [".o"],
        True,
        6,
        0.4,
    )
