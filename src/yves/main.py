"""Main script that will be called with `yves`."""

import argparse
import logging
import os

from lib.llm_summarizer import LLMSummarizer, generate_summary
from lib.llm_summarizer import update_from_config as llm_update_from_config


def main():
    """Execute main function."""
    global_parser = argparse.ArgumentParser(add_help=False)
    global_parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="~/.config/yves/config",
        help="Path to configuration file",
    )
    global_parser.add_argument("--debug", action="store_true", help="Debug logging")

    parser = argparse.ArgumentParser()
    sub_parsers = parser.add_subparsers(dest="command")
    sub_parsers.add_parser("init", parents=[global_parser], help="Initialize Yves")
    sub_parsers.add_parser("check", parents=[global_parser], help="Check if LLM works")
    sub_parsers.add_parser("summarize", parents=[global_parser], help="Summarize")
    sub_parsers.add_parser(
        "record", parents=[global_parser], help="Watch and summarize"
    )
    sub_parsers.add_parser(
        "describe", parents=[global_parser], help="Show configuration"
    )
    sub_parsers.add_parser("version", parents=[global_parser], help="Package version")
    p_args = parser.parse_args()

    if p_args.command is None:
        parser.print_help()
        exit(1)

    logging.basicConfig(
        level=logging.DEBUG if p_args.debug else logging.INFO,
        format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s",
    )

    logger = logging.getLogger(__name__)

    logger.debug(f"Subcommand: {p_args.command}")
    if p_args.command == "version":
        from importlib.metadata import version

        print(f"Yves {version('yves')}")
    elif p_args.command == "init":
        from lib.interactive import configure_interactively

        configure_interactively()
    elif p_args.command == "check":
        from lib.llm_summarizer import check

        config_path = os.path.expanduser(p_args.config)
        summarizer = LLMSummarizer()
        llm_update_from_config(summarizer, config_path)

        check(summarizer)
    elif p_args.command == "describe":
        from lib.cfg import parse_config, print_config

        config_path = os.path.expanduser(p_args.config)
        cfg = parse_config(config_path)
        print_config(cfg)
    elif p_args.command == "summarize":
        from threading import Event, Thread

        from lib.file_system_watcher import FileSystemWatcher
        from lib.file_system_watcher import update_from_config as fs_update_from_config
        from lib.file_system_watcher import watch as fs_watch
        from lib.signal import setup_signal_handler
        from lib.tmux_watcher import TmuxWatcher
        from lib.tmux_watcher import update_from_config as tmux_update_from_config
        from lib.tmux_watcher import watch as tmux_watch

        config_path = os.path.expanduser(p_args.config)

        summarizer = LLMSummarizer()
        llm_update_from_config(summarizer, config_path)

        empty_event = Event()
        generate_summary(summarizer, empty_event, wait_to_summarize=False)
    else:
        from threading import Event, Thread

        from lib.file_system_watcher import FileSystemWatcher
        from lib.file_system_watcher import update_from_config as fs_update_from_config
        from lib.file_system_watcher import watch as fs_watch
        from lib.signal import setup_signal_handler
        from lib.tmux_watcher import TmuxWatcher
        from lib.tmux_watcher import update_from_config as tmux_update_from_config
        from lib.tmux_watcher import watch as tmux_watch

        config_path = os.path.expanduser(p_args.config)

        fs_watcher = FileSystemWatcher()
        tmux_watcher = TmuxWatcher()
        summarizer = LLMSummarizer()
        llm_update_from_config(summarizer, config_path)

        stop_event = Event()
        setup_signal_handler(stop_event)

        threads = [
            Thread(target=generate_summary, args=(summarizer, stop_event)),
        ]

        if fs_watcher.enable:
            fs_update_from_config(fs_watcher, config_path)
            threads.append(Thread(target=fs_watch, args=(fs_watcher, stop_event)))

        if tmux_watcher.enable:
            tmux_update_from_config(tmux_watcher, config_path)
            threads.append(Thread(target=tmux_watch, args=(tmux_watcher, stop_event)))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
