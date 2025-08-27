#!/usr/bin/env python3
"""
Watch for file changes and capture only the diffs (changed content) to a text file.
This script monitors files for changes and saves the newly changed content without using git.
"""

import os
import argparse
import time
import hashlib
import difflib
import re
import fnmatch
from datetime import datetime


class FileWatcher:
    """
    File system monitor that captures changes as diffs from multiple repositories.
    """

    def __init__(
        self,
        watch_dirs: list[str],
        output_file: str = "changes.txt",
        file_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        major_changes_only: bool = False,
        min_lines_changed: int = 3,
        similarity_threshold: float = 0.7,
    ) -> None:
        """
        Initialize file watcher for multiple directories.

        Args:
            watch_dirs: List of directories to monitor
            output_file: Output file for diffs
            file_patterns: Include patterns (e.g., ['*.py', '*.js'])
            exclude_patterns: Exclude patterns (e.g., ['*.pyc', '__pycache__'])
            major_changes_only: Filter out minor changes
            min_lines_changed: Minimum lines for major change
            similarity_threshold: Minimum similarity ratio [0.0-1.0] for major change detection
        """
        self.watch_dirs: list[str] = [os.path.abspath(d) for d in watch_dirs]
        self.output_file: str = output_file
        self.file_patterns: list[str] = file_patterns or []
        self.exclude_patterns: list[str] = exclude_patterns or []
        self.file_snapshots: dict[str, dict[str, object]] = {}
        self.last_check: float = time.time()
        self.major_changes_only: bool = major_changes_only
        self.min_lines_changed: int = min_lines_changed
        self.similarity_threshold: float = similarity_threshold

    def is_binary_file(self, filepath: str) -> bool:
        """
        Check if file is binary by attempting to decode as UTF-8.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for _ in f:
                    continue
            return False
        except (OSError, UnicodeDecodeError):
            return True

    def should_watch_file(self, filepath: str) -> bool:
        """
        Check if file should be monitored based on patterns.

        Filtering order:
        1. Exclude output file (prevents infinite loops)
        2. Check exclude patterns
        3. Check include patterns (if any)
        4. Default: include all non-excluded files
        """
        # Always exclude the output file to prevent infinite monitoring loops
        output_path = os.path.abspath(self.output_file)
        if os.path.abspath(filepath) == output_path:
            return False

        # Find which watch directory this file belongs to
        watch_dir = self._get_watch_dir_for_file(filepath)
        if watch_dir is None:
            return False

        rel_path = os.path.relpath(filepath, watch_dir)

        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if self._matches_pattern(rel_path, pattern):
                return False

        # Check include patterns (if any specified)
        if self.file_patterns:
            for pattern in self.file_patterns:
                if self._matches_pattern(rel_path, pattern):
                    return True
            return False

        return True

    def _get_watch_dir_for_file(self, filepath: str) -> str | None:
        """
        Find which watch directory contains the given file.
        """
        for watch_dir in self.watch_dirs:
            try:
                rel_path = os.path.relpath(filepath, watch_dir)
                if not rel_path.startswith(".."):
                    return watch_dir
            except ValueError:
                # Different drives on Windows
                continue
        return None

    def _matches_pattern(self, filepath: str, pattern: str) -> bool:
        """
        Glob pattern matching using fnmatch.
        """
        return fnmatch.fnmatch(filepath, pattern)

    def get_file_hash(self, filepath: str) -> str | None:
        """
        Generate MD5 hash of file content for change detection.
        """
        try:
            with open(filepath, "rb") as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except OSError:
            return None

    def get_file_lines(self, filepath: str) -> list[str] | None:
        """
        Read text file as list of lines with UTF-8 encoding.
        """
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.readlines()
        except OSError:
            return None

    def generate_diff(
        self,
        old_lines: list[str] | None,
        new_lines: list[str] | None,
        filename: str,
    ) -> str | None:
        """
        Generate unified diff between two versions of a file.
        """
        if old_lines is None:
            old_lines = []
        if new_lines is None:
            return None

        diff = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{filename}",
                tofile=f"b/{filename}",
                lineterm="",
            )
        )

        return "\n".join(diff) if diff else None

    def normalize_line(self, line: str) -> str:
        """
        Normalize line for major change detection (strip whitespace, ignore comments).
        """
        if not self.major_changes_only:
            return line

        normalized = line.strip()

        # Skip empty lines and comments
        if not normalized or normalized.startswith("#") or normalized.startswith("//"):
            return ""

        # Normalize whitespace
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    def is_major_change(
        self,
        old_lines: list[str] | None,
        new_lines: list[str] | None,
        filepath: str,
    ) -> bool:
        """
        Determine if changes are significant enough to capture.

        Checks for:
        - Structural code changes (keywords like def, class, function, etc.)
        - Minimum lines changed threshold
        - Low similarity between lines (below similarity_threshold)
        """
        if not self.major_changes_only:
            return True

        # Normalize lines to focus on structural changes
        old_normalized = [self.normalize_line(line) for line in (old_lines or [])]
        new_normalized = [self.normalize_line(line) for line in (new_lines or [])]

        # Remove empty lines after normalization
        old_normalized = [line for line in old_normalized if line]
        new_normalized = [line for line in new_normalized if line]

        # Calculate differences
        old_set = set(old_normalized)
        new_set = set(new_normalized)
        added_lines = new_set - old_set
        removed_lines = old_set - new_set
        total_changes = len(added_lines) + len(removed_lines)

        # Check for code keywords in changes
        ext = os.path.splitext(filepath)[1].lower()
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
        if total_changes >= self.min_lines_changed:
            return True

        # Check for significant content changes (not just typos)
        for old_line, new_line in zip(old_normalized, new_normalized):
            if old_line != new_line:
                ratio = difflib.SequenceMatcher(None, old_line, new_line).ratio()
                if ratio < self.similarity_threshold:
                    return True

        return False

    def scan_files(self) -> list[str]:
        """
        Recursively scan all directories for files matching patterns.
        """
        files_to_watch = []
        for watch_dir in self.watch_dirs:
            for root, dirs, files in os.walk(watch_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    if self.should_watch_file(filepath):
                        files_to_watch.append(filepath)
        return files_to_watch

    def check_for_changes(self) -> list[dict[str, object]]:
        """
        Check all monitored files for changes and generate diffs.

        Returns list of changes with 'type', 'file', and 'diff' keys.
        Handles both text and binary files appropriately.
        """
        changes = []
        files = self.scan_files()

        for filepath in files:
            current_hash = self.get_file_hash(filepath)
            if current_hash is None:
                continue

            # Find which repository this file belongs to
            watch_dir = self._get_watch_dir_for_file(filepath)
            if watch_dir is None:
                continue

            # Handle binary files
            if self.is_binary_file(filepath):
                rel_path = os.path.relpath(filepath, watch_dir)
                repo_name = os.path.basename(watch_dir)

                if filepath not in self.file_snapshots:
                    changes.append(
                        {
                            "type": "new",
                            "file": filepath,
                            "diff": f"Binary file added: {repo_name}/{rel_path}",
                        }
                    )
                    self.file_snapshots[filepath] = {
                        "hash": current_hash,
                        "lines": None,
                        "is_binary": True,
                    }
                elif self.file_snapshots[filepath]["hash"] != current_hash:
                    changes.append(
                        {
                            "type": "modified",
                            "file": filepath,
                            "diff": f"Binary file modified: {repo_name}/{rel_path}",
                        }
                    )
                    self.file_snapshots[filepath] = {
                        "hash": current_hash,
                        "lines": None,
                        "is_binary": True,
                    }
                continue

            # Handle text files
            current_lines = self.get_file_lines(filepath)
            if current_lines is None:
                continue

            rel_path = os.path.relpath(filepath, watch_dir)
            repo_name = os.path.basename(watch_dir)

            if filepath not in self.file_snapshots:
                # New file
                if not self.major_changes_only or self.is_major_change(
                    None, current_lines, filepath
                ):
                    diff = self.generate_diff(
                        None, current_lines, f"{repo_name}/{rel_path}"
                    )
                    if diff:
                        changes.append({"type": "new", "file": filepath, "diff": diff})

                self.file_snapshots[filepath] = {
                    "hash": current_hash,
                    "lines": current_lines,
                    "is_binary": False,
                }
            elif self.file_snapshots[filepath]["hash"] != current_hash:
                # Changed file
                old_lines = self.file_snapshots[filepath].get("lines", [])

                if self.is_major_change(old_lines, current_lines, filepath):
                    diff = self.generate_diff(
                        old_lines, current_lines, f"{repo_name}/{rel_path}"
                    )
                    if diff:
                        changes.append(
                            {"type": "modified", "file": filepath, "diff": diff}
                        )
                else:
                    print(f"  Minor change ignored in: {repo_name}/{rel_path}")

                self.file_snapshots[filepath] = {
                    "hash": current_hash,
                    "lines": current_lines,
                    "is_binary": False,
                }

        return changes

    def write_changes_to_file(self, changes: list[dict[str, object]]) -> None:
        """
        Write detected changes to output file with timestamps and formatting.
        """
        if not changes:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 80}\n")
            f.write(f"CHANGES DETECTED AT: {timestamp}\n")
            f.write(f"{'=' * 80}\n")

            for change in changes:
                # Find the repository name for display
                watch_dir = self._get_watch_dir_for_file(change["file"])
                if watch_dir:
                    rel_path = os.path.relpath(change["file"], watch_dir)
                    repo_name = os.path.basename(watch_dir)
                    display_path = f"{repo_name}/{rel_path}"
                else:
                    display_path = change["file"]

                f.write(f"\n--- {change['type'].upper()}: {display_path} ---\n")
                f.write(change["diff"])
                f.write(f"\n--- END OF DIFF FOR {display_path} ---\n")

        print(f"Captured {len(changes)} file changes to {self.output_file}")
        for change in changes:
            watch_dir = self._get_watch_dir_for_file(change["file"])
            if watch_dir:
                rel_path = os.path.relpath(change["file"], watch_dir)
                repo_name = os.path.basename(watch_dir)
                display_path = f"{repo_name}/{rel_path}"
            else:
                display_path = change["file"]
            print(f"  {change['type']}: {display_path}")

    def watch(self) -> None:
        """
        Start monitoring loop. Runs until Ctrl+C is pressed.
        """
        print(f"Watching {len(self.watch_dirs)} repositories:")
        for watch_dir in self.watch_dirs:
            print(f"  - {watch_dir}")
        print(f"Output file: {self.output_file}")
        if self.file_patterns:
            print(f"Watching patterns: {self.file_patterns}")
        if self.exclude_patterns:
            print(f"Excluding patterns: {self.exclude_patterns}")
        print("Press Ctrl+C to stop watching...")
        print("-" * 50)

        # Initial scan to establish baseline
        print("Initial scan...")
        files = self.scan_files()
        for filepath in files:
            current_hash = self.get_file_hash(filepath)
            if current_hash:
                if self.is_binary_file(filepath):
                    self.file_snapshots[filepath] = {
                        "hash": current_hash,
                        "lines": None,
                        "is_binary": True,
                    }
                else:
                    current_lines = self.get_file_lines(filepath)
                    if current_lines is not None:
                        self.file_snapshots[filepath] = {
                            "hash": current_hash,
                            "lines": current_lines,
                            "is_binary": False,
                        }
        print(f"Monitoring {len(self.file_snapshots)} files")

        try:
            while True:
                time.sleep(1)
                changes = self.check_for_changes()
                if changes:
                    self.write_changes_to_file(changes)
        except KeyboardInterrupt:
            print("\nStopped watching directory")


def main() -> None:
    """
    Command-line interface for file change monitoring.
    """
    parser = argparse.ArgumentParser(
        description="Watch multiple repositories for file changes and capture diffs",
        epilog="""
Examples:
  %(prog)s . --output changes.txt
  %(prog)s /path/to/repo1 /path/to/repo2 --output changes.txt
  %(prog)s /path/to/code --patterns "*.py" "*.js" --output code_changes.txt
  %(prog)s . --exclude "*.pyc" "__pycache__" "*.log" --output filtered.txt
  %(prog)s . --major-only --min-lines 5 --output major.txt
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "watch_dirs", nargs="+", help="Directories to watch for changes"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="changes.txt",
        help="Output file for changes (default: changes.txt)",
    )
    parser.add_argument(
        "--patterns", nargs="*", help="File patterns to watch (e.g., *.py *.txt)"
    )
    parser.add_argument(
        "--exclude", nargs="*", help="Patterns to exclude (e.g., *.pyc __pycache__)"
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

    args = parser.parse_args()

    watcher = FileWatcher(
        watch_dirs=args.watch_dirs,
        output_file=args.output,
        file_patterns=args.patterns,
        exclude_patterns=args.exclude,
        major_changes_only=args.major_only,
        min_lines_changed=args.min_lines,
        similarity_threshold=args.similarity_threshold,
    )

    watcher.watch()


if __name__ == "__main__":
    main()
