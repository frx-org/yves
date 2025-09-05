def test_update_from_config(tmpdir):
    """Test `update_from_config` if it updates the current `TmuxWatcher` instance"""
    from configparser import ConfigParser
    from uuid import uuid4

    from lib.tmux_watcher import TmuxWatcher, update_from_config

    abs_path = tmpdir / f"{uuid4().hex}"
    default_watcher = TmuxWatcher([])
    watcher = TmuxWatcher([])

    config = ConfigParser()
    config["tmux"] = {
        "panes": "0 , 1,my_session:my_window.1",
        "output_file": "new_output_file.txt",
        "capture_full_output": "True",
    }
    with open(abs_path, "w") as f:
        config.write(f)

    update_from_config(watcher, abs_path)
    assert default_watcher != watcher
    assert watcher == TmuxWatcher(
        ["0", "1", "my_session:my_window.1"],
        "new_output_file.txt",
        True,
    )
