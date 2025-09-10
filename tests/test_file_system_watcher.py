def test_update_from_config(tmpdir):
    """Test `update_from_config` if it updates the current `FileSystemWatcher` instance"""
    import os
    from configparser import ConfigParser
    from uuid import uuid4

    from lib.file_system_watcher import FileSystemWatcher, update_from_config

    abs_path = tmpdir / f"{uuid4().hex}"
    default_watcher = FileSystemWatcher([])
    watcher = FileSystemWatcher([])

    config = ConfigParser()
    config["filesystem"] = {
        "dirs": "~, . ,/home/me",
        "output_file": "new_output_file.json",
        "include_filetypes": ".py ,.nix,.nu",
        "exclude_filetypes": ".o",
        "major_changes_only": "True",
        "min_lines_changed": "6",
        "similarity_threshold": "0.4",
    }
    with open(abs_path, "w") as f:
        config.write(f)

    update_from_config(watcher, abs_path)
    assert default_watcher != watcher
    assert watcher == FileSystemWatcher(
        [os.path.expanduser("~"), ".", "/home/me"],
        "new_output_file.json",
        [".py", ".nix", ".nu"],
        [".o"],
        True,
        6,
        0.4,
    )
