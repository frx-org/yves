import logging
import os
from configparser import ConfigParser

logger = logging.getLogger(__name__)


def default_config() -> ConfigParser:
    """Get default configuration.

    Returns
    -------
    dict[str, dict[str, object]]
        Default configuration values

    """
    config = ConfigParser(
        converters={
            "list": lambda vs: []
            if not vs.strip()
            else [v.strip() for v in vs.split(",")],
            "int": lambda n: int(n),
            "float": lambda n: float(n),
            "bool": lambda b: b.lower() == "true",
        }
    )
    config["filesystem"] = {
        "dirs": "",
        "output_file": "fs_changes.txt",
        "include_filetypes": "",
        "exclude_filetypes": "",
        "major_changes_only": "False",
        "min_lines_changed": "3",
        "similarity_threshold": "0.7",
    }
    config["tmux"] = {
        "panes": "",
        "output_file": "tmux_changes.txt",
        "capture_full_output": "False",
    }
    config["llm"] = {
        "api_key": "",
        "model_name": "",
        "provider": "",
    }
    config["summarizer"] = {
        "output_file": "summary_output.txt",
        "token_limit": "1000000",
        "at": "19:00",
    }

    return config


def write_default_config(path: str):
    """Write default configuration to a file.

    Parameters
    ----------
    path : str
        Path to write the default configuration file

    """

    parent_dir = os.path.dirname(path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    default_cfg = default_config()
    with open(path, "w") as f:
        default_cfg.write(f)
        logger.debug(f"Configuration file {path} updated")


def parse_config(
    path: str = os.path.join(os.path.expanduser("~"), ".config/recapify/config"),
) -> ConfigParser:
    """Read a config file as input and return the dictionary containing these values.
    If the configuration file does not exist, we create the default configuration.

    Parameters
    ----------
    path : str
        Path to the configuration file

    Returns
    -------
    ConfigParser
        Dictionary contained in the config file

    """
    from datetime import datetime

    if not os.path.exists(path):
        logger.debug(f"{path} does not exist, write default configuration file")
        write_default_config(path)

    user_config = ConfigParser(
        converters={
            "list": lambda vs: []
            if not vs.strip()
            else [v.strip() for v in vs.split(",")],
            "int": lambda n: int(n),
            "float": lambda n: float(n),
            "bool": lambda b: b.lower() == "true",
            "time": lambda t: datetime.strptime(t, "%H:%M").time(),
            "date": lambda d: datetime.strptime(d, "%Y-%m-%d").date(),
        }
    )
    user_config.read(path)

    return user_config
