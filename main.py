import argparse
import logging
import os
from threading import Event, Thread

from lib.file_system_watcher import FileSystemWatcher
from lib.file_system_watcher import update_from_config as fs_update_from_config
from lib.file_system_watcher import watch as fs_watch
from lib.llm_summarizer import LLMSummarizer, generate_summary
from lib.llm_summarizer import update_from_config as llm_update_from_config
from lib.signal import setup_signal_handler
from lib.tmux_watcher import TmuxWatcher
from lib.tmux_watcher import update_from_config as tmux_update_from_config
from lib.tmux_watcher import watch as tmux_watch

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="~/.config/recapify/config",
        help="Path to configuration file",
    )
    parser.add_argument("--debug", action="store_true", help="Debug logging")
    p_args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if p_args.debug else logging.INFO,
        format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s",
    )

    fs_watcher = FileSystemWatcher()
    tmux_watcher = TmuxWatcher()
    summarizer = LLMSummarizer()

    config_path = os.path.expanduser(p_args.config)

    fs_update_from_config(fs_watcher, config_path)
    tmux_update_from_config(tmux_watcher, config_path)
    llm_update_from_config(summarizer, config_path)

    stop_event = Event()
    setup_signal_handler(stop_event)

    threads = [
        Thread(target=fs_watch, args=(fs_watcher, stop_event)),
        Thread(target=tmux_watch, args=(tmux_watcher, stop_event)),
        Thread(target=generate_summary, args=(summarizer, stop_event)),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()
