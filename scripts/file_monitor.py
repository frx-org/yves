#!/usr/bin/env python3
"""
Main script to monitor files using FileWatcher from lib.
"""

import argparse
from lib.file_system_watcher import FileSystemWatcher, watch
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s",
)


def main() -> None:
    """Parse command line arguments and start the file watcher."""
    parser = argparse.ArgumentParser(
        description="Watch files for changes and capture diffs",
        epilog="""
Examples:
  %(prog)s . --output changes.txt
  %(prog)s /path/to/repo1 /path/to/repo2 --output changes.txt
  %(prog)s /path/to/code --include ".py" ".js" --output code_changes.txt
  %(prog)s . --exclude ".pyc" "__pycache__" ".log" --output filtered.txt
  %(prog)s . --major-only --min-lines 5 --output major.txt
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("dirs", nargs="+", help="Directories to watch for changes")
    parser.add_argument(
        "--output",
        "-o",
        default="changes.txt",
        help="Output file for changes",
    )
    parser.add_argument(
        "--include",
        nargs="*",
        default=[],
        help="File patterns to watch (e.g., .py .txt)",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Patterns to exclude (e.g., .pyc __pycache__)",
    )
    parser.add_argument(
        "--major-only",
        action="store_true",
        help="Only capture major changes (ignore typos, comments, whitespace)",
    )
    parser.add_argument(
        "--min-lines",
        type=int,
        default=3,
        help="Minimum lines changed to consider it major",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.7,
        help="Minimum similarity ratio [0.0-1.0] for major change detection",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=1,
        help="Check interval in seconds",
    )

    args = parser.parse_args()

    watcher = FileSystemWatcher(
        dirs=args.dirs,
        output_file=args.output,
        include_filetypes=args.include,
        exclude_filetypes=args.exclude,
        major_changes_only=args.major_only,
        min_lines_changed=args.min_lines,
        similarity_threshold=args.similarity_threshold,
    )

    watch(watcher, timeout=args.timeout)


if __name__ == "__main__":
    main()
