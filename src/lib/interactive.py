"""Interactive asking library."""

import logging
import os
from configparser import ConfigParser

import questionary

logger = logging.getLogger(__name__)


def ask_config_path() -> str:
    """Ask the user where do they want to store their configuration file. If the parent directory does not exist, we create it.

    Returns
    -------
    str
        Path to the configuration file

    """
    cfg_path = questionary.text(
        "Where do you want to store the configuration file?",
        default="~/.config/yves/config",
    ).ask()
    logger.debug(f"Configuration path: {cfg_path}")

    dir_cfg_path = os.path.expanduser(os.path.dirname(cfg_path))
    if not os.path.exists(dir_cfg_path):
        logger.debug(f"{dir_cfg_path} does not exist, creating it...")
        os.makedirs(dir_cfg_path, exist_ok=True)

    return cfg_path


def ask_overwrite_config(config_path: str) -> bool:
    """Ask the user if they want to overwrite the existing config.

    Parameters
    ----------
    config_path : str
        Path to configuration file.

    Returns
    -------
    bool
        `True` if they want to overwrite, else `False`.

    """
    overwrite = questionary.confirm(
        f"{config_path} already exists, do you want to overwrite its content?",
    ).ask()

    return overwrite


def ask_and_update_fs_enable(cfg: ConfigParser) -> bool:
    """Ask the user if they want to enable file system watch and update `cfg`.

    Parameters
    ----------
    cfg : ConfigParser
        Configuration instance to update

    Returns
    -------
    bool
        User answer

    """
    enable = questionary.confirm(
        "Would you want to enable the watcher on the filesystem?"
    ).ask()

    if enable:
        logger.debug("Enable filesystem watcher")
        cfg["filesystem"]["enable"] = "True"
    else:
        logger.debug("Disable filesystem watcher")
        cfg["filesystem"]["enable"] = "False"

    return enable


def ask_and_update_fs_dirs(cfg: ConfigParser) -> None:
    """Ask the user which directories they want to watch and update `cfg`.

    Parameters
    ----------
    cfg : ConfigParser
        Configuration instance to update

    """
    str_fs_dirs = ""
    while True:
        d = questionary.path(
            "Which directory do you want to watch (or leave empty to stop loop)?",
            only_directories=True,
        ).ask()

        if not d:
            break

        if str_fs_dirs:
            str_fs_dirs += f", {d}"
        else:
            str_fs_dirs = d

    logger.debug(f"Directories to watch on the file system: {str_fs_dirs}")
    cfg["filesystem"]["dirs"] = str_fs_dirs


def ask_and_update_fs_exclude(cfg: ConfigParser) -> None:
    """Ask they user what elements they want to exclude from the file system search and update `cfg`.

    Parameters
    ----------
    cfg : ConfigParser
        Configuration instance to update

    """
    exclude_filetypes = questionary.checkbox(
        "I suggest you to exclude some filetypes/directories to search faster, please select them:",
        choices=[
            questionary.Choice("*.pyc", checked=True),
            questionary.Choice("*.pyo", checked=True),
            questionary.Choice("*.pyd", checked=True),
            questionary.Choice("*.swp", checked=True),
            questionary.Choice("*.swo", checked=True),
            questionary.Choice("*~", checked=True),
            questionary.Choice(".git", checked=True),
        ],
    ).ask()
    str_exclude_filetypes = ", ".join([e.lstrip("*") for e in exclude_filetypes])

    logger.debug(f"Element to exclude: {str_exclude_filetypes}")
    cfg["filesystem"]["exclude_filetypes"] = str_exclude_filetypes


def ask_and_update_tmux_enable(cfg: ConfigParser) -> bool:
    """Ask the user if they want to enable tmux panes watch and update `cfg`.

    Parameters
    ----------
    cfg : ConfigParser
        Configuration instance to update

    Returns
    -------
    bool
        User answer

    """
    enable = questionary.confirm(
        "Would you want to enable the watcher on tmux panes?"
    ).ask()

    if enable:
        logger.debug("Enable tmux watcher")
        cfg["tmux"]["enable"] = "True"
    else:
        logger.debug("Disable tmux watcher")
        cfg["tmux"]["enable"] = "False"

    return enable


def ask_and_update_llm_provider(cfg: ConfigParser) -> None:
    """Ask the user about the LLM provider they want to use and update `cfg`.

    Parameters
    ----------
    cfg : ConfigParser
        Configuration instance to update

    """
    provider = questionary.text(
        "Which LLM provider do you want to use (refer to https://docs.litellm.ai/docs/providers)?",
        default="openai",
    ).ask()
    logger.debug(f"LLM Provider: {provider}")

    model_name = questionary.text(
        "Which model do you want to use (refer to https://docs.litellm.ai/docs/providers)?"
    ).ask()
    logger.debug(f"LLM model: {model_name}")

    api_key = questionary.password(
        "What is your API key (leave empty if your LLM provider does not need it)?"
    ).ask()
    logger.debug(f"API key for LLM provider: {api_key}")

    cfg["llm"]["api_key"] = api_key
    cfg["llm"]["model_name"] = model_name
    cfg["llm"]["provider"] = provider


def is_valid_hour(hour: str) -> bool:
    """Test if the string `hour` follows the correct date format.

    Parameters
    ----------
    hour : str
        String to test

    Returns
    -------
    bool
        Returns `True` if format is correct, else `False`

    """
    from datetime import datetime

    try:
        datetime.strptime(hour, "%H:%M")
        return True
    except ValueError:
        return False


def ask_and_update_summarizer(cfg: ConfigParser) -> None:
    """Ask the user how they want to get the summary.

    Parameters
    ----------
    cfg : ConfigParser
        Configure instance to update

    """
    summary_path = questionary.text(
        "Where do you want to store all summaries (give a directory)?",
        default="~/.local/share/yves",
    ).ask()
    logger.debug(f"Summary output directory: {summary_path}")

    expand_summary_path = os.path.expanduser(summary_path)
    if not os.path.exists(expand_summary_path):
        logger.debug(f"{summary_path} does not exist, creating it...")
        os.makedirs(expand_summary_path, exist_ok=True)

    summary_hour = questionary.text(
        'When do you want me to write the report (format: "%H:%m")?',
        default="19:00",
        validate=is_valid_hour,
    ).ask()
    logger.debug(f"Summary hour: {summary_hour}")

    cfg["summarizer"]["output_dir"] = summary_path
    cfg["summarizer"]["at"] = summary_hour


def is_valid_formatter(formatter: str) -> bool:
    """Check if the formatter exists.

    Parameters
    ----------
    formatter : str
        Formatter name

    Returns
    -------
    bool
        Returns `True` if the command exists.
        Note if equal to "None", we return `True`.

    """
    from lib.check import command_exists

    if formatter == "None":
        return True

    return command_exists(formatter)


def ask_formatter(cfg: ConfigParser, formatters: list[str]) -> None:
    """Ask the user if they want the summary to be formatted.

    Parameters
    ----------
    cfg : ConfigParser
        Configure instance to update
    formatters : list[str]
        List of allowed formatters

    """
    while True:
        formatter = questionary.select(
            "Do you want the summary to be automatically formatted? Choose one of the allowed formatters (you must have the formatter installed on your system)",
            choices=formatters,
        ).ask()

        if is_valid_formatter(formatter):
            break
        else:
            logger.error(
                f"You chose {formatter} but we cannot find this command on your system, please choose another answer"
            )

    if formatter == "None":
        logger.debug("No formatter chosen")
        cfg["formatter"]["enable"] = "False"
    else:
        logger.debug(f"Chosen formatter: {formatter}")
        cfg["formatter"]["enable"] = "True"
        cfg["formatter"]["command"] = formatter


def configure_interactively() -> None:
    """Interactively configure Yves with the user."""
    from textwrap import dedent

    from lib.cfg import default_config, print_config, write_config

    cfg = default_config()

    print(
        dedent("""\
        Hello, my name is Yves.

        I am going to ask you some questions to understand how you want me to summarize your day.
    """)
    )

    cfg_path = ask_config_path()
    cfg_exists = os.path.exists(os.path.expanduser(cfg_path))
    overwrite_cfg = False
    if cfg_exists:
        overwrite_cfg = ask_overwrite_config(cfg_path)

    if not cfg_exists or overwrite_cfg:
        fs_enable = ask_and_update_fs_enable(cfg)
        if fs_enable:
            ask_and_update_fs_dirs(cfg)
            ask_and_update_fs_exclude(cfg)

        _ = ask_and_update_tmux_enable(cfg)
        ask_and_update_llm_provider(cfg)
        ask_and_update_summarizer(cfg)
        ask_formatter(cfg, ["prettier", "None"])

        write_config(cfg, cfg_path)

        print(f"\nThis is your current configuration stored in {cfg_path}\n")
        print_config(cfg)
