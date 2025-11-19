"""Test lib/llm_summarizer.py."""


def test_update_from_config(tmp_path):
    """Test `update_from_config` if it updates the current `LLMSummarizer` instance."""
    from configparser import ConfigParser
    from datetime import datetime
    from uuid import uuid4

    from lib.llm_summarizer import LLMSummarizer, update_from_config

    abs_path = tmp_path / f"{uuid4().hex}"
    summarize_output_dir = tmp_path / "summarize_dir"
    default_summarizer = LLMSummarizer()
    summarizer = LLMSummarizer()

    config = ConfigParser()
    config["filesystem"] = {
        "output_file": "fs_output_file.json",
    }
    config["tmux"] = {
        "output_file": "tmux_output_file.json",
    }
    config["llm"] = {
        "api_key": "this-is-my-api-secret",
        "model_name": "gpt-4o-mini",
        "provider": "openai",
    }
    config["summarizer"] = {
        "output_dir": summarize_output_dir,
        "token_limit": "154546",
        "at": "15:49",
    }
    config["formatter"] = {
        "enable": "True",
        "command": "prettier",
    }
    with open(abs_path, "w") as f:
        config.write(f)

    update_from_config(summarizer, abs_path)
    assert default_summarizer != summarizer
    assert summarizer == LLMSummarizer(
        "this-is-my-api-secret",
        "gpt-4o-mini",
        "openai",
        "tmux_output_file.json",
        "fs_output_file.json",
        str(summarize_output_dir),
        154546,
        datetime.strptime("15:49", "%H:%M").time(),
        datetime.strptime("0001-01-01", "%Y-%m-%d").date(),
        "prettier",
    )


def test_format_summary(tmp_path):
    """Test `format_summary`."""
    import shutil
    from pathlib import Path
    from uuid import uuid4

    from lib.llm_summarizer import LLMSummarizer, format_summary

    llm_summarizer = LLMSummarizer()
    original_report = Path(__file__).parent / "samples" / "reports" / "original.md"
    copy_original_report = tmp_path / f"{uuid4().hex}.md"

    shutil.copyfile(original_report, copy_original_report)
    format_summary(llm_summarizer, str(copy_original_report))
    assert original_report.read_text() == copy_original_report.read_text()

    llm_summarizer.formatter = "non-existant_formatter"
    shutil.copyfile(original_report, copy_original_report)
    format_summary(llm_summarizer, str(copy_original_report))
    assert original_report.read_text() == copy_original_report.read_text()

    llm_summarizer.formatter = "prettier"
    shutil.copyfile(original_report, copy_original_report)
    format_summary(llm_summarizer, str(copy_original_report))
    prettier_report = Path(__file__).parent / "samples" / "reports" / "prettier.md"
    assert prettier_report.read_text() == copy_original_report.read_text()
