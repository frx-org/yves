import json
import logging
import os
from dataclasses import dataclass, field
from threading import Event

logger = logging.getLogger(__name__)


@dataclass
class FileSystemWatcher:
    """File system monitor that captures changes as diffs from multiple directories.

    Attributes
    ----------
    enable: Enable the watcher or not
    dirs: List of directories to monitor
    output_file: Output file for diffs
    tmux_output_file: Output file for tmux diffs
    summary_output_dir: Output directory for daily summaries
    include_filetypes: Include filetypes (e.g., ['.py', '.js'])
    exclude_filetypes: Exclude filetypes (e.g., ['.pyc'])
    major_changes_only: Filter out minor changes
    min_lines_changed: Minimum lines for major change
    similarity_threshold: Minimum similarity ratio [0.0-1.0] for major change detection
    file_snapshots: Dictionary containing stats files to watch
    """

    enable: bool = True
    dirs: list[str] = field(default_factory=list)
    output_file: str = "changes.json"
    tmux_output_file: str = "tmux_changes.json"
    summary_output_dir: str = os.path.expanduser("~/.local/state/yves")
    include_filetypes: list[str] = field(default_factory=list)
    exclude_filetypes: list[str] = field(default_factory=list)
    major_changes_only: bool = False
    min_lines_changed: int = 3
    similarity_threshold: float = 0.7
    file_snapshots: dict[str, dict[str, str | list[str] | bool]] = field(
        default_factory=dict
    )


def update_from_config(watcher: FileSystemWatcher, config_path: str) -> None:
    """Read a config file and update `watcher`.

    Parameters
    ----------
    watcher : FileSystemWatcher
        Watcher values to be updated
    config_path : str
        Path to the configuration file

    """
    from lib.cfg import parse_config

    cfg = parse_config(config_path)

    watcher.enable = cfg.getbool("filesystem", "enable")  # type: ignore
    watcher.dirs = [os.path.expanduser(p) for p in cfg.getlist("filesystem", "dirs")]  # type: ignore
    if len(watcher.dirs) == 0:
        logger.warning("No directory specified to watch")

    watcher.output_file = os.path.expanduser(cfg["filesystem"]["output_file"])
    watcher.tmux_output_file = os.path.expanduser(cfg["tmux"]["output_file"])
    watcher.summary_output_dir = os.path.expanduser(cfg["summarizer"]["output_dir"])
    watcher.include_filetypes = cfg.getlist("filesystem", "include_filetypes")  # type: ignore
    watcher.exclude_filetypes = cfg.getlist("filesystem", "exclude_filetypes")  # type: ignore
    watcher.major_changes_only = cfg.getbool("filesystem", "major_changes_only")  # type: ignore
    watcher.min_lines_changed = cfg.getint("filesystem", "min_lines_changed")
    watcher.similarity_threshold = cfg.getfloat("filesystem", "similarity_threshold")


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


def normalize_line(watcher: FileSystemWatcher, line: str) -> str:
    """Normalize line for major change detection (strip whitespace, ignore comments).

    Parameters
    ----------
    watcher : FileSystemWatcher
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
    watcher: FileSystemWatcher,
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
    watcher : FileSystemWatcher
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


def scan_files(watcher: FileSystemWatcher) -> list[str]:
    """Recursively scan all directories for files matching filetypes

    Parameters
    ----------
    watcher : FileSystemWatcher

    Returns
    -------
    list[str]
        List of files to watch

    """
    from datetime import date
    from functools import partial
    from glob import glob, iglob
    from time import time

    today = date.today().strftime("%Y-%m-%d")

    def exclude_filetypes_fn(path: str, exclude_filetypes: list[str]):
        return not any({path.endswith(filetype) for filetype in exclude_filetypes})

    def glob_fn(
        include_filetypes: list[str], exclude_filetypes: list[str], parent_dir: str
    ):
        result = []
        for include_filetype in include_filetypes:
            result_glob = glob(f"{parent_dir}/**/*{include_filetype}", recursive=True)
            num_elements_found = len(result_glob)
            if num_elements_found > 0:
                logger.debug(
                    f"Found {num_elements_found} {include_filetype} files in {parent_dir}"
                )
            else:
                logger.debug(f"No {include_filetype} file in {parent_dir}")

            result += result_glob

        if len(result) == 0:
            if len(include_filetypes) > 0:
                return []

            logger.debug(f"Listing any files in {parent_dir}")
            result = iglob(f"{parent_dir}/**/*", recursive=True)
            logger.debug(f"Found {len(list(result))} elements in {parent_dir}")

        logger.debug(f"Excluding filetypes in {parent_dir}")
        result = filter(
            partial(exclude_filetypes_fn, exclude_filetypes=exclude_filetypes),
            result,
        )

        return result

    t_start = time()
    files_to_watch = []
    for watch_dir in watcher.dirs:
        logger.debug(f"Searching for files in {watch_dir}")
        for p in glob_fn(
            watcher.include_filetypes, watcher.exclude_filetypes, watch_dir
        ):
            # always exclude the output file to prevent infinite monitoring loops
            abs_output_path = os.path.abspath(watcher.output_file)
            abs_tmux_output_path = os.path.abspath(watcher.tmux_output_file)
            abs_summary_output_dir = os.path.abspath(
                os.path.join(watcher.summary_output_dir, f"{today}.md")
            )

            abs_p = os.path.abspath(p)

            not_output_file = abs_p != abs_output_path
            not_tmux_output_file = abs_p != abs_tmux_output_path
            not_summary_output_dir = abs_p != abs_summary_output_dir

            if (
                not_output_file
                and not_tmux_output_file
                and not_summary_output_dir
                and os.path.isfile(p)
            ):
                files_to_watch.append(p)

    logger.debug(f"Scanning took {time() - t_start}s")

    return files_to_watch


def check_for_changes(
    watcher: FileSystemWatcher,
) -> list[dict[str, str | list[str] | bool]]:
    """Check all monitored files for changes and generate diffs.

    Handles both text and binary files appropriately.

    Parameters
    ----------
    watcher : FileSystemWatcher

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

        # Find which directory this file belongs to
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
                logger.debug(f"Minor change ignored in: {repo_name}/{rel_path}")

            watcher.file_snapshots[filepath] = {
                "hash": current_hash,
                "lines": current_lines,
                "is_binary": False,
            }

    return changes


def write_changes_to_file(
    watcher: FileSystemWatcher, changes: list[dict[str, str | list[str] | bool]]
) -> None:
    """Write detected changes to output file with timestamps and formatting.

    Parameters
    ----------
    watcher : FileSystemWatcher
    changes : list[dict[str, str | list[str] | bool]]
      List of changes to write in `watcher.output_file`

    """
    from datetime import datetime

    from lib.file import find_file_in_dirs

    if not changes:
        return

    timestamp = int(datetime.now().timestamp())

    # Load existing JSON if the file exists
    if os.path.exists(watcher.output_file):
        with open(watcher.output_file, "r", encoding="utf-8") as f:
            try:
                all_events = json.load(f)
            except json.JSONDecodeError:
                all_events = []
    else:
        all_events = []

    # Append new changes
    changes_list = []
    for change in changes:
        watch_dir = find_file_in_dirs(change["file"], watcher.dirs)  # type: ignore
        if watch_dir:
            rel_path = os.path.relpath(change["file"], watch_dir)  # type: ignore
            repo_name = os.path.basename(os.path.normpath(watch_dir))
            display_path = f"{repo_name}/{rel_path}"
        else:
            display_path = change["file"]

        changes_list.append(
            {
                "file": display_path,
                "status": change["type"].lower(),  # e.g., "modified", "new"
                "diff": change.get("diff", "").splitlines()
                if isinstance(change.get("diff"), str)
                else change.get("diff", []),
                "is_binary": change.get("is_binary", False),
            }
        )

    all_events.append(
        {
            "event_type": "changes_detected",
            "timestamp": timestamp,
            "changes": changes_list,
        }
    )

    output_dir = os.path.dirname(watcher.output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Write updated JSON back to file
    with open(watcher.output_file, "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    # Logging
    logger.debug(f"Captured {len(changes)} file changes to {watcher.output_file}")
    for change in changes_list:
        logger.debug(f"{change['status']}: {change['file']}")


def watch(watcher: FileSystemWatcher, stop_event: Event, timeout: int = 1) -> None:
    """Start monitoring loop. Runs until Ctrl+C is pressed.

    Parameters
    ----------
    watcher : FileSystemWatcher
        The watcher instance to monitor
    stop_event : Event
        Event sent to stop watching
    timeout : int
        Timeout in seconds in the while loop

    """

    from time import sleep

    from lib.file import get_content, get_md5, is_binary

    logger.debug(f"Watching {len(watcher.dirs)} directories:")
    for watch_dir in watcher.dirs:
        logger.debug(watch_dir)
    logger.debug(f"Output file: {watcher.output_file}")
    if watcher.include_filetypes:
        logger.debug(f"Watching filetypes: {watcher.include_filetypes}")
    if watcher.exclude_filetypes:
        logger.debug(f"Excluding filetypes: {watcher.exclude_filetypes}")

    logger.debug("Initial scan...")
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
        logger.debug(file_snapshot)

    logger.info("Watching for changes...")
    while not stop_event.is_set():
        changes = check_for_changes(watcher)
        if changes:
            logger.debug(f"Found {len(changes)} changes")
            write_changes_to_file(watcher, changes)

        sleep(timeout)
