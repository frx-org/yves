"""Test lib/interactive.py."""

import os

import questionary


def test_ask_config_path(tmp_path, monkeypatch):
    """Test `ask_config_path` if it creates the directory and return the right answer."""
    from uuid import uuid4

    from lib.interactive import ask_config_path

    dir_cfg_path = tmp_path / f"{uuid4().hex}"
    cfg_path = dir_cfg_path / "config"
    assert not os.path.exists(cfg_path)
    assert not dir_cfg_path.exists()

    monkeypatch.setattr("questionary.Question.ask", lambda _: str(cfg_path))
    result = ask_config_path()

    assert result == str(cfg_path)
    assert dir_cfg_path.exists()


def test_ask_and_update_fs_enable(monkeypatch):
    """Test `ask_and_update_fs_enable`."""
    from lib.cfg import ConfigParser
    from lib.interactive import ask_and_update_fs_enable

    cfg = ConfigParser()
    cfg["filesystem"] = {}

    monkeypatch.setattr(questionary.Question, "ask", lambda _: True)
    result = ask_and_update_fs_enable(cfg)
    assert result is True
    assert cfg["filesystem"]["enable"] == "True"

    monkeypatch.setattr(questionary.Question, "ask", lambda _: False)
    result = ask_and_update_fs_enable(cfg)
    assert result is False
    assert cfg["filesystem"]["enable"] == "False"


def test_ask_and_update_fs_dirs(monkeypatch):
    """Test `ask_and_update_fs_dirs`."""
    from lib.cfg import ConfigParser
    from lib.interactive import ask_and_update_fs_dirs

    answers = iter(["/tmp/a/directory", "~/test/another/directory", ""])
    monkeypatch.setattr("questionary.Question.ask", lambda _: next(answers))

    cfg = ConfigParser()
    cfg["filesystem"] = {}

    ask_and_update_fs_dirs(cfg)

    assert cfg["filesystem"]["dirs"] == "/tmp/a/directory, ~/test/another/directory"


def test_ask_and_update_fs_exclude(monkeypatch):
    """Test `ask_and_update_fs_exclude`."""
    from lib.cfg import ConfigParser
    from lib.interactive import ask_and_update_fs_exclude

    answers = ["*.pyo", "*~", ".git"]
    monkeypatch.setattr("questionary.Question.ask", lambda _: answers)

    cfg = ConfigParser()
    cfg["filesystem"] = {}

    ask_and_update_fs_exclude(cfg)

    assert cfg["filesystem"]["exclude_filetypes"] == ".pyo, ~, .git"


def test_ask_and_update_tmux_enable(monkeypatch):
    """Test `ask_and_update_tmux_enable`."""
    from lib.cfg import ConfigParser
    from lib.interactive import ask_and_update_tmux_enable

    cfg = ConfigParser()
    cfg["tmux"] = {}

    monkeypatch.setattr(questionary.Question, "ask", lambda _: True)
    result = ask_and_update_tmux_enable(cfg)
    assert result is True
    assert cfg["tmux"]["enable"] == "True"

    monkeypatch.setattr(questionary.Question, "ask", lambda _: False)
    result = ask_and_update_tmux_enable(cfg)
    assert result is False
    assert cfg["tmux"]["enable"] == "False"


def test_ask_and_update_llm_provider(monkeypatch):
    """Test `ask_and_update_llm_provider`."""
    from lib.cfg import ConfigParser
    from lib.interactive import ask_and_update_llm_provider

    answers = iter(["anthropic", "claude-opus-4-1-20250805", "my-VERY-private-$3Cr37"])
    monkeypatch.setattr("questionary.Question.ask", lambda _: next(answers))

    cfg = ConfigParser()
    cfg["llm"] = {}

    ask_and_update_llm_provider(cfg)

    assert cfg["llm"] == {
        "api_key": "my-VERY-private-$3Cr37",
        "model_name": "claude-opus-4-1-20250805",
        "provider": "anthropic",
    }


def test_is_valid_hour():
    """Test `is_valid_hour`."""
    from lib.interactive import is_valid_hour

    assert is_valid_hour("19:00")
    assert is_valid_hour("00:00")
    assert not is_valid_hour("wrong-hour")
    assert not is_valid_hour("25:00")
    assert not is_valid_hour("10:86")
    assert not is_valid_hour("98:86")
    assert not is_valid_hour("-00:00")
    assert not is_valid_hour("-10:01")


def test_ask_and_update_summarizer(tmp_path, monkeypatch):
    """Test `ask_and_update_summarizer` by also creating the directory if it does not exist yet."""
    from uuid import uuid4

    from lib.cfg import ConfigParser
    from lib.interactive import ask_and_update_summarizer

    summary_dir = tmp_path / f"{uuid4().hex}" / "summaries"
    assert not summary_dir.exists()

    answers = iter([str(summary_dir), "19:30"])

    monkeypatch.setattr("questionary.Question.ask", lambda _: next(answers))
    cfg = ConfigParser()
    cfg["summarizer"] = {}
    ask_and_update_summarizer(cfg)

    assert cfg["summarizer"] == {"output_dir": str(summary_dir), "at": "19:30"}
    assert summary_dir.exists()
