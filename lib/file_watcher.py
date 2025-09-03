import logging
import os
from dataclasses import dataclass, field
from types import FrameType

logger = logging.getLogger(__name__)


@dataclass
class FileWatcher:
    """File system monitor that captures changes as diffs from multiple repositories.

    Attributes
    ----------
    dirs: List of directories to monitor
    output_file: Output file for diffs
    file_patterns: Include patterns (e.g., ['*.py', '*.js'])
    exclude_patterns: Exclude patterns (e.g., ['*.pyc', '__pycache__'])
    major_changes_only: Filter out minor changes
    min_lines_changed: Minimum lines for major change
    similarity_threshold: Minimum similarity ratio [0.0-1.0] for major change detection
    file_snapshots: Dictionary containing stats files to watch
    """

    dirs: list[str]
    output_file: str = "changes.txt"
    file_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    major_changes_only: bool = False
    min_lines_changed: int = 3
    similarity_threshold: float = 0.7
    file_snapshots: dict[str, dict[str, str | list[str] | bool]] = field(
        default_factory=dict
    )


def should_watch_file(watcher: FileWatcher, file_path: str) -> bool:
    """Check if file should be monitored based on patterns.

    Filtering order:
    1. Exclude output file (prevents infinite loops)
    2. Check exclude patterns
    3. Default: include all non-excluded files

    Parameters
    ----------
    watcher : FileWatcher
    file_path : str
        Path to the file we analyze to watch or not

    Returns
    -------
    bool
        `True` is `file_path` should be watched, else `False`

    """

    from fnmatch import fnmatch

    from lib.file import find_file_in_dirs

    # Always exclude the output file to prevent infinite monitoring loops
    output_path = os.path.abspath(watcher.output_file)
    if os.path.abspath(file_path) == output_path:
        return False

    watch_dir = find_file_in_dirs(file_path, watcher.dirs)
    if watch_dir is None:
        return False

    rel_path = os.path.relpath(file_path, watch_dir)

    for pattern in watcher.exclude_patterns:
        if fnmatch(rel_path, pattern):
            return False

    return True


def generate_diff(
    old_lines: list[str],
    new_lines: list[str],
    file_name: str,
) -> str | None:
    """Generate unified diff between two versions of a file.

    Parameters
    ----------
    old_lines : list[str]
        List of previous lines before modification on the file
    new_lines : list[str]
        List of new lines after modification on the file
    file_name : str
        Filename of the file

    Returns
    -------
    str | None
        Diff between two versions

    """
    from difflib import unified_diff

    diff = list(
        unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_name}",
            tofile=f"b/{file_name}",
            lineterm="",
        )
    )

    return "\n".join(diff) if diff else None


def normalize_line(watcher: FileWatcher, line: str) -> str:
    """Normalize line for major change detection (strip whitespace, ignore comments).

    Parameters
    ----------
    watcher : FileWatcher
    line : str
        Line to normalize

    Returns
    -------
    str
       Normalized `line`

    """
    from re import sub

    if not watcher.major_changes_only:
        return line

    normalized = line.strip()

    # Skip empty lines and comments
    if not normalized or normalized.startswith("#") or normalized.startswith("//"):
        return ""

    # Normalize whitespace
    normalized = sub(r"\s+", " ", normalized)
    return normalized


def is_major_change(
    watcher: FileWatcher,
    old_lines: list[str],
    new_lines: list[str],
    file_path: str,
) -> bool:
    """Determine if changes are significant enough to capture.

    Checks for:
    - Structural code changes (keywords like def, class, function, etc.)
    - Minimum lines changed threshold
    - Low similarity between lines (below similarity_threshold)

    Parameters
    ----------
    watcher : FileWatcher
    old_lines : list[str]
        List of previous lines before modification on the file
    new_lines : list[str]
        List of new lines after modification on the file
    file_path : str
        Path to the file to check

    Returns
    -------
    bool
        `True` if `file_path` has majorly changed, else `False`

    """
    from difflib import SequenceMatcher

    if not watcher.major_changes_only:
        return True

    # Normalize lines to focus on structural changes
    old_normalized = [normalize_line(watcher, line) for line in old_lines]
    new_normalized = [normalize_line(watcher, line) for line in new_lines]

    # Remove empty lines after normalization
    old_set = set(line for line in old_normalized if line)
    new_set = set(line for line in new_normalized if line)

    # Calculate differences
    added_lines = new_set - old_set
    removed_lines = old_set - new_set
    total_changes = len(added_lines) + len(removed_lines)

    # Check for code keywords in changes
    ext = os.path.splitext(file_path)[1].lower()

    # TODO: need to generalize more filetypes
    if ext in [".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs"]:
        code_keywords = [
            "def ",
            "class ",
            "function ",
            "import ",
            "from ",
            "if ",
            "for ",
            "while ",
            "return ",
            "async ",
            "await ",
            "try ",
            "except ",
            "catch ",
            "throw ",
            "func ",
            "fn ",
            "match ",
        ]
        for line in added_lines.union(removed_lines):
            if any(keyword in line.lower() for keyword in code_keywords):
                return True

    # Check minimum lines threshold
    if total_changes >= watcher.min_lines_changed:
        return True

    # Check for significant content changes (not just typos)
    for old_line, new_line in zip(old_normalized, new_normalized):
        if old_line != new_line:
            ratio = SequenceMatcher(None, old_line, new_line).ratio()
            if ratio < watcher.similarity_threshold:
                return True

    return False


def scan_files(watcher: FileWatcher) -> list[str]:
    """Recursively scan all directories for files matching patterns

    Parameters
    ----------
    watcher : FileWatcher

    Returns
    -------
    list[str]
        List of files to watch

    """
    from glob import iglob
    from time import time

    def glob_fn(file_patterns, parent_dir):
        result = []
        for file_pattern in file_patterns:
            result += iglob(f"{parent_dir}/**/{file_pattern}", recursive=True)

        if len(result) == 0:
            if len(file_patterns) > 0:
                return []

            result = iglob(f"{parent_dir}/**/*", recursive=True)

        return result

    t_start = time()
    files_to_watch = [
        p
        for watch_dir in watcher.dirs
        for p in glob_fn(watcher.file_patterns, watch_dir)
        if (should_watch_file(watcher, p) and os.path.isfile(p))
    ]
    logging.debug(f"Scanning took {time() - t_start}s")

    return files_to_watch


def check_for_changes(watcher: FileWatcher) -> list[dict[str, str | list[str] | bool]]:
    """Check all monitored files for changes and generate diffs.

    Handles both text and binary files appropriately.

    Parameters
    ----------
    watcher : FileWatcher

    Returns
    -------
    list[dict[str, object]]
        Returns list of changes with 'type', 'file', and 'diff' keys.

    """
    from lib.file import find_file_in_dirs, get_content, get_md5, is_binary

    changes = []
    files = scan_files(watcher)

    for filepath in files:
        current_hash = get_md5(filepath)
        if current_hash is None:
            continue

        # Find which repository this file belongs to
        watch_dir = find_file_in_dirs(filepath, watcher.dirs)
        if watch_dir is None:
            continue

        # Handle binary files
        if is_binary(filepath):
            rel_path = os.path.relpath(filepath, watch_dir)
            repo_name = os.path.basename(watch_dir)

            if filepath not in watcher.file_snapshots:
                changes.append(
                    {
                        "type": "new",
                        "file": filepath,
                        "diff": f"Binary file added: {repo_name}/{rel_path}",
                    }
                )
                watcher.file_snapshots[filepath] = {
                    "hash": current_hash,
                    "lines": [],
                    "is_binary": True,
                }
            elif watcher.file_snapshots[filepath]["hash"] != current_hash:
                changes.append(
                    {
                        "type": "modified",
                        "file": filepath,
                        "diff": f"Binary file modified: {repo_name}/{rel_path}",
                    }
                )
                watcher.file_snapshots[filepath] = {
                    "hash": current_hash,
                    "lines": [],
                    "is_binary": True,
                }
            continue

        # Handle text files
        current_lines = get_content(filepath)
        if current_lines is None:
            continue

        rel_path = os.path.relpath(filepath, watch_dir)
        repo_name = os.path.basename(watch_dir)

        if filepath not in watcher.file_snapshots:
            # New file
            if not watcher.major_changes_only or is_major_change(
                watcher, [], current_lines, filepath
            ):
                diff = generate_diff([], current_lines, f"{repo_name}/{rel_path}")
                if diff:
                    changes.append({"type": "new", "file": filepath, "diff": diff})

            watcher.file_snapshots[filepath] = {
                "hash": current_hash,
                "lines": current_lines,
                "is_binary": False,
            }
        elif watcher.file_snapshots[filepath]["hash"] != current_hash:
            # Changed file
            old_lines: list[str] = watcher.file_snapshots[filepath]["lines"]  # type: ignore

            if is_major_change(watcher, old_lines, current_lines, filepath):
                diff = generate_diff(
                    old_lines, current_lines, f"{repo_name}/{rel_path}"
                )
                if diff:
                    changes.append({"type": "modified", "file": filepath, "diff": diff})
            else:
                logger.debug(f"  Minor change ignored in: {repo_name}/{rel_path}")

            watcher.file_snapshots[filepath] = {
                "hash": current_hash,
                "lines": current_lines,
                "is_binary": False,
            }

    return changes


def write_changes_to_file(
    watcher: FileWatcher, changes: list[dict[str, str | list[str] | bool]]
) -> None:
    """Write detected changes to output file with timestamps and formatting.

    Parameters
    ----------
    watcher : FileWatcher
    changes : list[dict[str, str | list[str] | bool]]
      List of changes to write in `watcher.output_file`

    """
    from datetime import datetime

    from lib.file import find_file_in_dirs

    if not changes:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(watcher.output_file, "w+", encoding="utf-8") as f:
        f.write(f"\n{'=' * 80}\n")
        f.write(f"CHANGES DETECTED AT: {timestamp}\n")
        f.write(f"{'=' * 80}\n")

        for change in changes:
            # Find the repository name for display
            watch_dir = find_file_in_dirs(change["file"], watcher.dirs)  # type: ignore
            if watch_dir:
                rel_path = os.path.relpath(change["file"], watch_dir)  # type: ignore
                repo_name = os.path.basename(watch_dir)
                display_path = f"{repo_name}/{rel_path}"
            else:
                display_path = change["file"]

            f.write(f"\n--- {change['type'].upper()}: {display_path} ---\n")  # type: ignore
            f.write(change["diff"])  # type: ignore
            f.write(f"\n--- END OF DIFF FOR {display_path} ---\n")

    logger.info(f"Captured {len(changes)} file changes to {watcher.output_file}")
    for change in changes:
        watch_dir = find_file_in_dirs(change["file"], watcher.dirs)  # type: ignore
        if watch_dir:
            rel_path = os.path.relpath(change["file"], watch_dir)  # type: ignore
            repo_name = os.path.basename(watch_dir)
            display_path = f"{repo_name}/{rel_path}"
        else:
            display_path = change["file"]
        logger.info(f"  {change['type']}: {display_path}")


def signal_handler(signal: int, frame: FrameType | None):
    """Handle signal. For now we suppose that we only catch SIGTERM and SIGINT to cleanly exit the program.
    This function is supposed to be called with `signal.signal(SIG, signal_handler)`

    Parameters
    ----------
    signal : int
        First argument needed by `signal.signal`
    frame : FrameType | None
        Second argument needed by `signal.signal`

    """
    from sys import exit

    exit(0)


def watch(watcher: FileWatcher, timeout: int = 1) -> None:
    """Start monitoring loop. Runs until Ctrl+C is pressed.

    Parameters
    ----------
    watcher : FileWatcher
    timeout : int
        Timeout in seconds in the while loop

    """

    from signal import SIGINT, SIGTERM, signal
    from time import sleep

    from lib.file import get_content, get_md5, is_binary

    logger.info(f"Watching {len(watcher.dirs)} repositories:")
    for watch_dir in watcher.dirs:
        logger.info(f"  - {watch_dir}")
    logger.info(f"Output file: {watcher.output_file}")
    if watcher.file_patterns:
        logger.info(f"Watching patterns: {watcher.file_patterns}")
    if watcher.exclude_patterns:
        logger.info(f"Excluding patterns: {watcher.exclude_patterns}")
    logger.info("Press Ctrl+C to stop watching...")
    logger.info("-" * 50)

    logger.info("Initial scan...")
    file_paths = scan_files(watcher)
    for file_path in file_paths:
        current_hash = get_md5(file_path)
        if is_binary(file_path):
            watcher.file_snapshots[file_path] = {
                "hash": current_hash,
                "lines": [],
                "is_binary": True,
            }
        else:
            current_lines = get_content(file_path)
            if current_lines is not None:
                watcher.file_snapshots[file_path] = {
                    "hash": current_hash,
                    "lines": current_lines,
                    "is_binary": False,
                }

    logger.debug(f"Monitoring {len(watcher.file_snapshots)} files")
    for file_snapshot in watcher.file_snapshots:
        logger.debug(f" - {file_snapshot}")

    signal(SIGTERM, signal_handler)
    signal(SIGINT, signal_handler)

    logging.info("Watching for changes...")
    while True:
        changes = check_for_changes(watcher)
        if changes:
            logging.debug(f"Found {len(changes)} changes")
            write_changes_to_file(watcher, changes)

        sleep(timeout)
