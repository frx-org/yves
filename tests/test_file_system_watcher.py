def test_update_from_config():
    """Test `update_from_config` if it updates the current `FileSystemWatcher` instance"""
    import os
    from configparser import ConfigParser
    from uuid import uuid4

    from lib.file_system_watcher import FileSystemWatcher, update_from_config

    abs_path = os.path.join("/tmp/new/dir/here", f"{uuid4().hex}")
    if not os.path.exists(os.path.dirname(abs_path)):
        os.makedirs(abs_path, exist_ok=True)

    default_watcher = FileSystemWatcher([])
    watcher = FileSystemWatcher([])

    config = ConfigParser()
    config["filesystem"] = {
        "dirs": "~, . ,/home/me",
        "output_file": "new_output_file.txt",
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
        ["~", ".", "/home/me"],
        "new_output_file.txt",
        [".py", ".nix", ".nu"],
        [".o"],
        True,
        6,
        0.4,
    )
