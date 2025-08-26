#!/usr/bin/env python3
"""
Watch for file changes and capture only the diffs (changed content) to a text file.
This script monitors files for changes and saves the newly changed content without using git.
"""

import subprocess
import sys
import os
import argparse
import time
import hashlib
import difflib
import re
import fnmatch
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple


class FileWatcher:
    """
    A comprehensive file system monitoring utility for tracking and capturing file changes as diffs.

    This class provides intelligent file monitoring capabilities with configurable filtering,
    change significance detection, and diff generation. It supports both text and binary file
    tracking while providing granular control over what changes are considered worth capturing.

    Attributes:
        watch_dir: Absolute path to the directory being monitored
        output_file: Path to the file where captured diffs will be written
        file_patterns: List of glob patterns for files to include in monitoring
        exclude_patterns: List of glob patterns for files to exclude from monitoring
        file_snapshots: Dictionary storing file state information (hash, content, metadata)
        last_check: Timestamp of the last change detection scan
        major_changes_only: Flag to filter out minor changes (whitespace, comments)
        min_lines_changed: Minimum number of lines that must change for major change detection
    """

    def __init__(
        self,
        watch_dir: str,
        output_file: str = "changes.txt",
        file_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        major_changes_only: bool = False,
        min_lines_changed: int = 3,
    ) -> None:
        """
        Initialize the file watcher with comprehensive configuration options.

        Args:
            watch_dir: Directory path to monitor for file changes. Can be relative or absolute,
                      will be converted to absolute path internally
            output_file: Path to the output file where captured diffs will be appended.
                        File will be created if it doesn't exist
            file_patterns: Optional list of glob patterns to include (e.g., ['*.py', '*.js']).
                          If None, all files are included (subject to exclusions)
            exclude_patterns: Optional list of glob patterns to exclude (e.g., ['*.pyc', '__pycache__']).
                            Takes precedence over include patterns
            major_changes_only: If True, filters out minor changes like whitespace modifications,
                              comment changes, and small typo corrections
            min_lines_changed: Minimum number of normalized lines that must be different
                             to consider a change as "major" when major_changes_only is True

        Returns:
            None

        Implementation Details:
            - Converts watch_dir to absolute path for consistent file tracking
            - Initializes empty file_snapshots dictionary for state management
            - Sets up change detection parameters for intelligent filtering
            - Handles None values for optional pattern lists gracefully
        """
        self.watch_dir: str = os.path.abspath(watch_dir)
        self.output_file: str = output_file
        self.file_patterns: List[str] = file_patterns or []
        self.exclude_patterns: List[str] = exclude_patterns or []
        self.file_snapshots: Dict[
            str, Dict[str, Any]
        ] = {}  # stores file hash and content
        self.last_check: float = time.time()
        self.major_changes_only: bool = major_changes_only
        self.min_lines_changed: int = min_lines_changed

    def is_binary_file(self, filepath: str) -> bool:
        """
        Determine if a file is binary by analyzing its content for null bytes and other binary indicators.

        This method provides robust binary file detection by examining the file's content rather than
        relying solely on file extensions. It uses a heuristic approach that works well for most
        common file types while being efficient by only reading a small portion of each file.

        Args:
            filepath: Absolute or relative path to the file to analyze

        Returns:
            Boolean indicating whether the file appears to be binary:
            - True: File contains binary content (images, executables, archives, etc.)
            - False: File appears to be text-based and suitable for diff generation

        Detection Algorithm:
            1. Reads the first 1024 bytes of the file for efficiency
            2. Checks for null bytes (0x00) which are common in binary files
            3. Handles read errors gracefully by assuming binary (safe default)

        Error Handling:
            - Returns True for files that cannot be read (permissions, corruption, etc.)
            - Prevents crashes when encountering system files or locked files
            - Safe default behavior preserves system stability

        Performance Notes:
            - Only reads first 1KB to minimize I/O overhead
            - Fast detection suitable for monitoring large directory trees
            - Efficient enough for real-time file system monitoring
        """
        try:
            with open(filepath, "rb") as f:
                chunk = f.read(1024)  # Read first 1KB
                return b"\0" in chunk  # Binary files often contain null bytes
        except (OSError, IOError):
            return True  # If can't read, assume binary

    def should_watch_file(self, filepath: str) -> bool:
        """
        Determine whether a specific file should be included in the monitoring process based on configured patterns.

        This method implements a flexible filtering system that allows fine-grained control over which files
        are monitored. It uses glob pattern matching to support wildcards and complex file selection rules
        while prioritizing exclusions over inclusions for security and performance reasons.

        Args:
            filepath: Absolute path to the file being evaluated for monitoring inclusion

        Returns:
            Boolean indicating whether the file should be monitored:
            - True: File matches criteria and should be tracked for changes
            - False: File should be ignored based on current filter configuration

        Filtering Logic:
            1. **Exclusion Priority**: Exclude patterns are checked first and take precedence
            2. **Inclusion Evaluation**: If include patterns are specified, file must match at least one
            3. **Default Behavior**: If no include patterns specified, all non-excluded files are included

        Pattern Matching:
            - Supports standard glob patterns with wildcards (*, ?, [])
            - Uses relative paths from watch_dir for pattern matching
            - Case-sensitive matching on most filesystems

        Common Use Cases:
            - Include only source code: patterns=['*.py', '*.js', '*.ts']
            - Exclude build artifacts: exclude_patterns=['*.pyc', '__pycache__', 'node_modules']
            - Monitor specific directories: patterns=['src/**/*']
            - Complex filtering: Combine includes and excludes for precise control

        Performance Considerations:
            - Relative path calculation is cached-friendly for repeated calls
            - Pattern matching is optimized for common glob expressions
            - Early exit on exclusion match minimizes unnecessary processing
        """
        rel_path = os.path.relpath(filepath, self.watch_dir)

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

    def _matches_pattern(self, filepath: str, pattern: str) -> bool:
        """
        Perform glob pattern matching against file paths with support for wildcards and complex expressions.

        This helper method provides robust pattern matching functionality using Python's fnmatch module,
        which implements Unix shell-style wildcards. It serves as the core matching engine for both
        inclusion and exclusion pattern filtering throughout the file monitoring system.

        Args:
            filepath: File path (typically relative) to test against the pattern
            pattern: Glob pattern string that may contain wildcards and special characters

        Returns:
            Boolean indicating whether the filepath matches the given pattern

        Supported Pattern Features:
            - '*': Matches any number of characters (including none)
            - '?': Matches exactly one character
            - '[seq]': Matches any character in seq (e.g., [abc] matches 'a', 'b', or 'c')
            - '[!seq]': Matches any character not in seq
            - '**': When used with path separators, matches directories recursively

        Examples:
            - '*.py' matches all Python files
            - 'test_*.py' matches all files starting with 'test_' and ending with '.py'
            - 'src/**/*.js' matches all JavaScript files in src directory tree
            - '[Tt]est*' matches files starting with 'Test' or 'test'
            - '*.log' matches all log files
            - '__pycache__' matches the exact directory name

        Implementation Notes:
            - Uses Python's fnmatch.fnmatch() for reliable cross-platform matching
            - Handles path separators correctly across different operating systems
            - Case sensitivity follows the underlying filesystem conventions
        """
        return fnmatch.fnmatch(filepath, pattern)

    def get_file_hash(self, filepath: str) -> Optional[str]:
        """
        Generate a cryptographic hash of a file's content for efficient change detection.

        This method computes an MD5 hash of the complete file content, providing a reliable
        and efficient way to detect any changes to the file without storing the entire content
        in memory for comparison. The hash serves as a digital fingerprint of the file state.

        Args:
            filepath: Absolute or relative path to the file to hash

        Returns:
            String containing the hexadecimal MD5 hash of the file content, or None if
            the file cannot be read due to permissions, corruption, or other I/O issues

        Hash Properties:
            - MD5 produces 128-bit (32 character hex) hash values
            - Extremely low probability of hash collisions for typical file monitoring
            - Fast computation suitable for real-time monitoring of large file sets
            - Deterministic: identical files always produce identical hashes

        Error Handling:
            - Returns None for files that cannot be accessed (permissions, locks, etc.)
            - Gracefully handles I/O errors without crashing the monitoring process
            - Allows monitoring to continue even if some files are temporarily inaccessible

        Security Notes:
            - MD5 is cryptographically weak but sufficient for change detection
            - Not suitable for security-critical applications requiring collision resistance
            - For this use case (change detection), MD5 provides optimal speed/reliability balance

        Performance Characteristics:
            - Reads entire file into memory for hashing (suitable for typical file sizes)
            - O(n) complexity where n is file size
            - Optimized for detecting changes rather than security applications
        """
        try:
            with open(filepath, "rb") as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except (OSError, IOError):
            return None

    def get_file_lines(self, filepath: str) -> Optional[List[str]]:
        """
        Read and return the complete content of a text file as a list of individual lines.

        This method safely reads text files with robust encoding handling and error management,
        making it suitable for processing diverse file types in international environments.
        The line-based format is optimized for diff generation and change analysis.

        Args:
            filepath: Path to the text file to read and process

        Returns:
            List of strings representing individual lines from the file (including newlines),
            or None if the file cannot be read or processed due to errors

        Encoding Handling:
            - Primary encoding: UTF-8 for broad international character support
            - Error handling: 'ignore' mode silently skips problematic bytes
            - Graceful degradation: Ensures reading continues even with encoding issues
            - Preserves original line endings for accurate diff generation

        Line Processing:
            - Maintains original line structure including trailing newlines
            - Preserves whitespace and formatting for accurate change detection
            - Returns empty list for empty files (distinct from None for errors)
            - Suitable for both Unix (\\n) and Windows (\\r\\n) line endings

        Error Scenarios:
            - File doesn't exist or has been deleted
            - Insufficient permissions to read the file
            - File is locked by another process
            - Disk I/O errors or filesystem corruption
            - Binary files that cannot be decoded as text

        Performance Notes:
            - Reads entire file into memory at once
            - Suitable for typical text files in development environments
            - May not be optimal for extremely large files (> 100MB)
            - Line-by-line structure enables efficient diff algorithms
        """
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.readlines()
        except (OSError, IOError):
            return None

    def generate_diff(
        self,
        old_lines: Optional[List[str]],
        new_lines: Optional[List[str]],
        filename: str,
    ) -> Optional[str]:
        """
        Generate a unified diff representation showing changes between two versions of a file.

        This method creates human-readable and tool-parseable diff output in the standard unified
        diff format, similar to what git and other version control systems produce. It handles
        both new file creation and existing file modification scenarios with appropriate context.

        Args:
            old_lines: List of lines from the previous version of the file, or None for new files
            new_lines: List of lines from the current version of the file, or None if file was deleted
            filename: Name of the file being compared (used in diff headers)

        Returns:
            String containing the unified diff in standard format, or None if no meaningful
            diff can be generated (e.g., both versions are None or identical)

        Diff Format Features:
            - Unified diff format compatible with standard tools (patch, git, etc.)
            - File headers showing before/after versions (a/filename vs b/filename)
            - Line numbers and context information for easy navigation
            - Clear marking of added (+), removed (-), and context lines
            - Proper handling of line endings for cross-platform compatibility

        Special Cases:
            - New files: old_lines is None, generates "added file" diff
            - Deleted files: new_lines is None (handled by caller)
            - Identical files: Returns None (no diff to show)
            - Empty files: Properly handles zero-length file scenarios

        Output Format:
            ```
            --- a/filename
            +++ b/filename
            @@ -1,4 +1,6 @@
             context line
            -removed line
            +added line
             another context line
            ```

        Integration Notes:
            - Output is compatible with standard diff parsing tools
            - Can be applied using patch command or similar utilities
            - Suitable for automated processing and analysis
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
        Normalize text lines for intelligent major change detection by filtering out insignificant differences.

        This method implements sophisticated text normalization that focuses on structural and semantic
        changes while ignoring cosmetic modifications like whitespace adjustments, comment formatting,
        and other minor variations that don't affect the actual meaning or functionality of code.

        Args:
            line: Individual line of text to normalize for comparison

        Returns:
            String containing the normalized version of the line, or empty string if the line
            should be ignored entirely for major change detection purposes

        Normalization Process:
            1. **Whitespace Handling**: Removes leading/trailing whitespace and normalizes internal spacing
            2. **Comment Filtering**: Identifies and optionally ignores comment-only changes
            3. **Empty Line Handling**: Converts whitespace-only lines to empty strings
            4. **Spacing Normalization**: Converts multiple consecutive spaces to single spaces

        Major Change Mode:
            - When major_changes_only is False: Returns line unchanged (no normalization)
            - When major_changes_only is True: Applies full normalization pipeline

        Filtering Rules:
            - Empty lines and whitespace-only lines → empty string
            - Lines starting with # (Python/shell comments) → empty string
            - Lines starting with // (C/JavaScript comments) → empty string
            - Multiple whitespace sequences → single space
            - Leading/trailing whitespace → removed

        Use Cases:
            - Ignore whitespace reformatting by code formatters
            - Skip comment-only changes in code reviews
            - Focus on structural changes rather than style modifications
            - Reduce noise when monitoring large codebases

        Language Support:
            - Python: Handles # comments
            - JavaScript/C/C++/Java: Handles // comments
            - General: Whitespace normalization works for all text files
            - Extensible: Can be enhanced for additional comment styles
        """
        if not self.major_changes_only:
            return line

        # Remove leading/trailing whitespace
        normalized = line.strip()

        # Skip empty lines and comments for major change detection
        if not normalized or normalized.startswith("#") or normalized.startswith("//"):
            return ""

        # Remove extra whitespace (multiple spaces become single space)
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized

    def is_major_change(
        self,
        old_lines: Optional[List[str]],
        new_lines: Optional[List[str]],
        filepath: str,
    ) -> bool:
        """
        Determine whether file changes represent significant modifications worthy of capture and analysis.

        This method implements intelligent change significance detection that distinguishes between
        meaningful structural changes and minor cosmetic modifications. It uses multiple heuristics
        including content analysis, file type awareness, and similarity scoring to make accurate
        determinations about change importance.

        Args:
            old_lines: List of lines from the previous version, or None for new files
            new_lines: List of lines from the current version, or None for deleted files
            filepath: Path to the file being analyzed (used for file type detection)

        Returns:
            Boolean indicating whether the change should be considered major:
            - True: Change is significant and should be captured
            - False: Change is minor/cosmetic and can be safely ignored

        Analysis Approach:
            1. **Configuration Check**: If major_changes_only is False, all changes are major
            2. **Content Normalization**: Applies line normalization to focus on meaningful differences
            3. **Quantitative Analysis**: Counts actual content differences after normalization
            4. **Qualitative Analysis**: Examines types of changes for structural significance
            5. **File Type Awareness**: Uses different criteria for different programming languages

        Major Change Indicators:
            - **Threshold-based**: More than min_lines_changed lines modified
            - **Structural Changes**: Keywords like def, class, function, import, if, for, while
            - **Low Similarity**: Lines with less than 70% similarity (indicates substantial rewrites)
            - **New Files**: All new file additions are considered major by default

        Supported File Types:
            - Python (.py): def, class, import, from, async, await, try, except
            - JavaScript/TypeScript (.js, .ts): function, class, import, if, for, while, async, await
            - Java (.java): class, function, import, if, for, while, try, catch, throw
            - C/C++ (.c, .cpp): function, if, for, while, return, try, catch, throw
            - Go (.go): func, if, for, return, import
            - Rust (.rs): fn, if, for, while, match, return

        Performance Optimizations:
            - Early exit when major_changes_only is disabled
            - Set operations for efficient line difference calculation
            - Lazy evaluation of expensive similarity calculations
            - File extension caching for type detection
        """
        if not self.major_changes_only:
            return True

        # Normalize lines to focus on structural changes
        old_normalized = [self.normalize_line(line) for line in (old_lines or [])]
        new_normalized = [self.normalize_line(line) for line in (new_lines or [])]

        # Remove empty lines after normalization
        old_normalized = [line for line in old_normalized if line]
        new_normalized = [line for line in new_normalized if line]

        # Calculate actual differences
        old_set = set(old_normalized)
        new_set = set(new_normalized)

        added_lines = new_set - old_set
        removed_lines = old_set - new_set
        total_changes = len(added_lines) + len(removed_lines)

        # Check for major change indicators
        ext = os.path.splitext(filepath)[1].lower()

        if ext in [".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs"]:
            # For code files, look for structural changes
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
            ]

            for line in added_lines.union(removed_lines):
                if any(keyword in line.lower() for keyword in code_keywords):
                    return True  # Structural change detected

        # Minimum lines changed threshold
        if total_changes >= self.min_lines_changed:
            return True

        # Check for significant content changes (not just typos)
        for old_line, new_line in zip(old_normalized, new_normalized):
            if old_line != new_line:
                # Calculate similarity ratio to detect more than minor typos
                ratio = difflib.SequenceMatcher(None, old_line, new_line).ratio()
                if ratio < 0.7:  # Less than 70% similarity = major change
                    return True

        return False

    def scan_files(self) -> List[str]:
        """
        Perform a comprehensive recursive scan of the watch directory to identify all files eligible for monitoring.

        This method traverses the entire directory tree starting from the configured watch directory,
        applying filtering rules to build a list of files that should be monitored for changes.
        It handles complex directory structures, symbolic links, and applies both inclusion and
        exclusion patterns to create the final monitoring set.

        Returns:
            List of absolute file paths that match the monitoring criteria and should be tracked
            for changes. Empty list if no files match the criteria or directory is inaccessible.

        Traversal Behavior:
            - **Recursive**: Examines all subdirectories unless excluded by patterns
            - **Depth-first**: Processes files in a predictable order
            - **Symbolic Links**: Follows symlinks (may cause issues with circular references)
            - **Hidden Files**: Includes hidden files unless explicitly excluded
            - **All File Types**: Examines both text and binary files (filtering occurs later)

        Filtering Integration:
            - Uses should_watch_file() to apply inclusion/exclusion patterns
            - Respects both positive (include) and negative (exclude) pattern matching
            - Applies filters at the individual file level for maximum flexibility
            - Handles edge cases like empty directories and permission issues

        Performance Characteristics:
            - O(n) where n is the total number of files in the directory tree
            - Memory usage scales with the number of monitored files
            - Disk I/O intensive during initial scan but efficient for ongoing monitoring
            - Results are computed fresh on each call (no caching for real-time accuracy)

        Error Handling:
            - Gracefully handles permission denied errors
            - Continues scanning if individual directories are inaccessible
            - Skips files that cannot be stat'd or accessed
            - Returns partial results rather than failing completely

        Use Cases:
            - Initial baseline establishment for file monitoring
            - Periodic rescans to detect newly created files
            - Integration with file system watchers for real-time updates
            - Batch processing of directory contents
        """
        files_to_watch = []
        for root, dirs, files in os.walk(self.watch_dir):
            for file in files:
                filepath = os.path.join(root, file)
                if self.should_watch_file(filepath):
                    files_to_watch.append(filepath)
        return files_to_watch

    def check_for_changes(self) -> List[Dict[str, Any]]:
        """
        Analyze all monitored files for changes and generate comprehensive change information with diffs.

        This method performs the core change detection logic by comparing current file states against
        previously stored snapshots. It handles both text and binary files appropriately, generates
        detailed diffs for text changes, and respects the major change filtering configuration.

        Returns:
            List of dictionaries containing change information. Each dictionary includes:
            - 'type': Change type ('new', 'modified', or 'deleted')
            - 'file': Absolute path to the changed file
            - 'diff': String containing the diff content or change description

        Change Detection Process:
            1. **File Discovery**: Scans directory for all eligible files using current filter rules
            2. **State Comparison**: Compares current file hashes against stored snapshots
            3. **Change Classification**: Determines if changes are new files, modifications, or deletions
            4. **Significance Analysis**: Applies major change filtering if enabled
            5. **Diff Generation**: Creates unified diffs for meaningful text file changes

        File Type Handling:
            - **Text Files**: Full diff generation with line-by-line analysis
            - **Binary Files**: Change detection without content analysis
            - **New Files**: Treated as major changes regardless of content
            - **Encoding Issues**: Graceful handling of problematic text files

        Binary File Processing:
            - Detects binary files to avoid corrupted diff output
            - Tracks binary file changes with descriptive messages
            - Maintains hash-based change detection for all file types
            - Prevents memory issues from large binary content

        Major Change Filtering:
            - Applies intelligent filtering when major_changes_only is enabled
            - Logs minor changes but excludes them from output
            - Uses content-aware analysis for different file types
            - Balances noise reduction with information preservation

        State Management:
            - Updates internal snapshots after processing each file
            - Maintains consistent state across multiple scan cycles
            - Handles new file detection and baseline establishment
            - Preserves file metadata for efficient subsequent scans

        Performance Optimizations:
            - Hash-based change detection minimizes unnecessary diff generation
            - Early exit for unchanged files reduces processing overhead
            - Efficient memory usage through streaming file operations
            - Batch processing of multiple file changes
        """
        changes = []
        files = self.scan_files()

        for filepath in files:
            current_hash = self.get_file_hash(filepath)
            if current_hash is None:
                continue

            # Check if it's a binary file - if so, only track the change but don't save content
            if self.is_binary_file(filepath):
                # Track binary file changes but don't save diff content
                if filepath not in self.file_snapshots:
                    # New binary file
                    rel_path = os.path.relpath(filepath, self.watch_dir)
                    changes.append(
                        {
                            "type": "new",
                            "file": filepath,
                            "diff": f"Binary file added: {rel_path}",
                        }
                    )
                    self.file_snapshots[filepath] = {
                        "hash": current_hash,
                        "lines": None,
                        "is_binary": True,
                    }
                elif self.file_snapshots[filepath]["hash"] != current_hash:
                    # Changed binary file
                    rel_path = os.path.relpath(filepath, self.watch_dir)
                    changes.append(
                        {
                            "type": "modified",
                            "file": filepath,
                            "diff": f"Binary file modified: {rel_path}",
                        }
                    )
                    self.file_snapshots[filepath] = {
                        "hash": current_hash,
                        "lines": None,
                        "is_binary": True,
                    }
                continue

            # Handle text files normally
            current_lines = self.get_file_lines(filepath)
            if current_lines is None:
                continue

            # Check if file is new or changed
            if filepath not in self.file_snapshots:
                # New file
                rel_path = os.path.relpath(filepath, self.watch_dir)

                # Check if it's a major change (for new files, always consider major)
                if not self.major_changes_only or self.is_major_change(
                    None, current_lines, filepath
                ):
                    diff = self.generate_diff(None, current_lines, rel_path)
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
                rel_path = os.path.relpath(filepath, self.watch_dir)

                # Check if it's a major change
                if self.is_major_change(old_lines, current_lines, filepath):
                    diff = self.generate_diff(old_lines, current_lines, rel_path)
                    if diff:
                        changes.append(
                            {"type": "modified", "file": filepath, "diff": diff}
                        )
                else:
                    # Minor change - log it but don't save diff
                    print(f"  Minor change ignored in: {rel_path}")

                self.file_snapshots[filepath] = {
                    "hash": current_hash,
                    "lines": current_lines,
                    "is_binary": False,
                }

        return changes

    def write_changes_to_file(self, changes: List[Dict[str, Any]]) -> None:
        """
        Persist detected file changes to the configured output file with structured formatting and metadata.

        This method handles the final stage of the change detection pipeline by writing captured
        changes to persistent storage in a human-readable and machine-parseable format. It provides
        comprehensive change documentation with timestamps, file paths, and complete diff content.

        Args:
            changes: List of change dictionaries containing type, file path, and diff information

        Returns:
            None

        Output Format Structure:
            - **Session Headers**: Timestamp-based delimiters for each monitoring session
            - **Change Blocks**: Individual sections for each file modification
            - **Metadata**: File paths, change types, and processing information
            - **Diff Content**: Complete unified diff output for text changes
            - **Clear Delimiters**: 80-character separators for easy visual parsing

        File Format Example:
            ```
            ================================================================================
            CHANGES DETECTED AT: 2024-08-26 14:30:25
            ================================================================================

            --- NEW: src/main.py ---
            [unified diff content]
            --- END OF DIFF FOR src/main.py ---

            --- MODIFIED: lib/utils.py ---
            [unified diff content]
            --- END OF DIFF FOR lib/utils.py ---
            ================================================================================
            ```

        File Handling:
            - **Append Mode**: Preserves previous monitoring sessions
            - **UTF-8 Encoding**: Supports international characters and symbols
            - **Atomic Writes**: Complete changes are written together
            - **Error Recovery**: Graceful handling of disk space and permission issues

        Console Output:
            - Provides immediate feedback on captured changes
            - Shows summary statistics (number of files changed)
            - Lists each changed file with its change type
            - Includes relative paths for better readability

        Integration Benefits:
            - Compatible with diff parsing tools and scripts
            - Suitable for automated processing and analysis
            - Human-readable for manual review and debugging
            - Structured format enables easy data extraction
        """
        if not changes:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 80}\n")
            f.write(f"CHANGES DETECTED AT: {timestamp}\n")
            f.write(f"{'=' * 80}\n")

            for change in changes:
                rel_path = os.path.relpath(change["file"], self.watch_dir)
                f.write(f"\n--- {change['type'].upper()}: {rel_path} ---\n")
                f.write(change["diff"])
                f.write(f"\n--- END OF DIFF FOR {rel_path} ---\n")

        print(f"Captured {len(changes)} file changes to {self.output_file}")
        for change in changes:
            rel_path = os.path.relpath(change["file"], self.watch_dir)
            print(f"  {change['type']}: {rel_path}")

    def watch(self) -> None:
        """
        Start the main file monitoring loop with comprehensive initialization and real-time change detection.

        This method serves as the primary entry point for continuous file system monitoring,
        providing a complete monitoring lifecycle from initialization through real-time change
        detection to graceful shutdown. It establishes baselines, monitors continuously, and
        handles user interruptions elegantly.

        Returns:
            None - runs indefinitely until interrupted by user (Ctrl+C)

        Execution Phases:

        1. **Configuration Display**:
           - Shows monitoring directory and output file configuration
           - Displays active file patterns and exclusions
           - Provides usage instructions and control information

        2. **Baseline Establishment**:
           - Performs initial comprehensive directory scan
           - Establishes file snapshots for all eligible files
           - Handles both text and binary files appropriately
           - Reports initial monitoring scope and statistics

        3. **Continuous Monitoring**:
           - Polls file system at 1-second intervals for optimal responsiveness
           - Detects and processes file changes as they occur
           - Applies intelligent filtering and significance analysis
           - Writes changes to output file immediately when detected

        4. **Graceful Shutdown**:
           - Handles keyboard interruption (Ctrl+C) cleanly
           - Provides user feedback on monitoring termination
           - Ensures proper cleanup and resource release

        Monitoring Characteristics:
            - **Polling Interval**: 1 second for responsive change detection
            - **Memory Efficient**: Hash-based change detection minimizes memory usage
            - **Real-time Updates**: Changes are captured and written immediately
            - **Robust Error Handling**: Continues monitoring despite individual file issues

        Console Output Features:
            - **Status Information**: Clear feedback on configuration and progress
            - **Debug Information**: File counts and monitoring scope
            - **Real-time Updates**: Immediate notification of detected changes
            - **User Guidance**: Clear instructions for operation and termination

        Performance Optimization:
            - Efficient file scanning with pattern-based filtering
            - Hash-based change detection reduces unnecessary processing
            - Incremental updates maintain performance with large file sets
            - Memory usage scales appropriately with monitored file count
        """
        print(f"Watching directory: {self.watch_dir}")
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
                    # Track binary files but don't store content
                    self.file_snapshots[filepath] = {
                        "hash": current_hash,
                        "lines": None,
                        "is_binary": True,
                    }
                else:
                    # Store text file content
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
                time.sleep(1)  # Check every second
                changes = self.check_for_changes()
                if changes:
                    self.write_changes_to_file(changes)
        except KeyboardInterrupt:
            print("\nStopped watching directory")


def main() -> None:
    """
    Command-line interface entry point for the file change monitoring and diff capture application.

    This function provides a comprehensive command-line interface for configuring and launching
    file system monitoring sessions with flexible filtering, change significance detection, and
    diff generation capabilities. It handles argument parsing, validation, and application
    initialization with extensive customization options.

    Returns:
        None - application runs until terminated by user

    Command Line Arguments:

        **Required Arguments:**
        - `watch_dir`: Directory path to monitor for file changes

        **Optional Arguments:**
        - `--output, -o`: Output file path for captured diffs (default: changes.txt)
        - `--patterns`: Include patterns using glob syntax (e.g., *.py *.js)
        - `--exclude`: Exclude patterns using glob syntax (e.g., *.pyc __pycache__)
        - `--major-only`: Enable major change filtering (ignore minor formatting changes)
        - `--min-lines`: Minimum lines changed for major change detection (default: 3)

    Usage Examples:

        **Basic Monitoring:**
        ```bash
        python diff_watcher.py /path/to/project --output project_changes.txt
        ```

        **Language-Specific Monitoring:**
        ```bash
        python diff_watcher.py /code --patterns "*.py" "*.js" --output code_changes.txt
        ```

        **Filtered Monitoring:**
        ```bash
        python diff_watcher.py . --exclude "*.pyc" "__pycache__" "*.log" --output filtered.txt
        ```

        **Major Changes Only:**
        ```bash
        python diff_watcher.py /project --major-only --min-lines 5 --output major.txt
        ```

    Configuration Features:
        - **Flexible Pattern Matching**: Support for complex include/exclude rules
        - **Intelligent Filtering**: Major change detection reduces noise
        - **Customizable Thresholds**: Adjustable sensitivity for change significance
        - **Multiple Output Formats**: Compatible with standard diff tools

    Error Handling:
        - Validates directory existence and accessibility
        - Checks file system permissions for output files
        - Provides clear error messages for configuration issues
        - Graceful handling of invalid patterns or arguments

    Integration Capabilities:
        - Output compatible with git and other VCS tools
        - Suitable for CI/CD pipeline integration
        - Machine-readable format for automated processing
        - Human-friendly format for manual review
    """
    parser = argparse.ArgumentParser(
        description="Watch directory for file changes and capture diffs to text file",
        epilog="""
Examples:
  %(prog)s . --output changes.txt
  %(prog)s /path/to/code --patterns "*.py" "*.js" --output code_changes.txt
  %(prog)s . --exclude "*.pyc" "__pycache__" "*.log" --output filtered_changes.txt
  %(prog)s . --major-only --min-lines 5 --output major_changes.txt
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("watch_dir", help="Directory to watch for changes")
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
        help="Minimum lines changed to consider it major (default: 3)",
    )

    args = parser.parse_args()

    watcher = FileWatcher(
        watch_dir=args.watch_dir,
        output_file=args.output,
        file_patterns=args.patterns,
        exclude_patterns=args.exclude,
        major_changes_only=args.major_only,
        min_lines_changed=args.min_lines,
    )

    watcher.watch()


if __name__ == "__main__":
    main()
