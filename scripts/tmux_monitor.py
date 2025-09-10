#!/usr/bin/env python3
"""
Main script to monitor tmux panes using TmuxWatcher from lib.
"""

import argparse
from lib.tmux_watcher import TmuxWatcher, watch
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s",
)


def main() -> None:
    """Parse command line arguments and start the tmux pane watcher."""
    parser = argparse.ArgumentParser(
        description="Watch tmux panes for command completion and capture outputs",
        epilog="""
Examples:
  %(prog)s 0 1 --output tmux_log.json
  %(prog)s my_session:0.0 --full-output
  %(prog)s 0 --output session.log
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--panes",
        nargs="+",
        help="List of tmux panes to watch (e.g., 0, 1, my_session:my_window.1)",
        default=[],
    )
    parser.add_argument(
        "--output",
        "-o",
        default="changes.json",
        help="Output file for command outputs",
    )
    parser.add_argument(
        "--full-output",
        action="store_true",
        help="Capture full pane content instead of just last command",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=1,
        help="Check interval in seconds",
    )

    args = parser.parse_args()

    # Create TmuxWatcher instance
    watcher = TmuxWatcher(
        panes=args.panes, output_file=args.output, capture_full_output=args.full_output
    )

    # Start watching
    watch(watcher, timeout=args.timeout)


if __name__ == "__main__":
    main()
