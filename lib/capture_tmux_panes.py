import subprocess
import re
import sys

def get_all_panes():
    """Get all tmux panes."""
    result = subprocess.run([
        "tmux", "list-panes", "-a", "-F", "#{session_name}:#{window_index}.#{pane_index}"
    ], capture_output=True, text=True)
    return result.stdout.strip().splitlines()

def get_session_panes(session):
    """Get all panes from a specific session."""
    result = subprocess.run([
        "tmux", "list-panes", "-t", session, "-F", "#{session_name}:#{window_index}.#{pane_index}"
    ], capture_output=True, text=True)
    return result.stdout.strip().splitlines()

def sanitize_pane_name(pane):
    """Replace : and . with _ for valid filenames."""
    return re.sub(r'[:.]', '_', pane)

def capture_all_panes():
    """Capture all tmux panes to separate files."""
    panes = get_all_panes()
    for pane in panes:
        filename = f"pane_{sanitize_pane_name(pane)}.txt"
        output = subprocess.run(["tmux", "capture-pane", "-t", pane, "-p"], capture_output=True, text=True).stdout
        with open(filename, "w") as f:
            f.write(output)
        print(f"Captured {pane} to {filename}")

def capture_all_to_one(output_file):
    """Capture all tmux panes to one file."""
    panes = get_all_panes()
    with open(output_file, "w") as f:
        for pane in panes:
            f.write(f"=== {pane} ===\n")
            output = subprocess.run(["tmux", "capture-pane", "-t", pane, "-p"], capture_output=True, text=True).stdout
            f.write(output)
            f.write("\n")
    print(f"All panes captured to {output_file}")

def capture_session(session):
    """Capture all panes from a specific session to separate files."""
    panes = get_session_panes(session)
    for pane in panes:
        filename = f"pane_{sanitize_pane_name(pane)}.txt"
        output = subprocess.run(["tmux", "capture-pane", "-t", pane, "-p"], capture_output=True, text=True).stdout
        with open(filename, "w") as f:
            f.write(output)
        print(f"Captured {pane} to {filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tmux_capture.py all           # Capture all panes to separate files")
        print("  python tmux_capture.py one <file>    # Capture all panes to one file")
        print("  python tmux_capture.py session <name> # Capture session to separate files")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "all":
        capture_all_panes()
    elif command == "one" and len(sys.argv) >= 3:
        capture_all_to_one(sys.argv[2])
    elif command == "session" and len(sys.argv) >= 3:
        capture_session(sys.argv[2])
    else:
        print("Invalid usage. See help above.")
        sys.exit(1)
