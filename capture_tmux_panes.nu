#!/usr/bin/env nu

# Capture all tmux panes to files
def capture_all_panes [] {
    # Get all panes
    let panes = (tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index}' | lines)

    for pane in $panes {
        let filename = $"pane_($pane | str replace -a ':' '_' | str replace -a '.' '_').txt"
        tmux capture-pane -t $pane -p | save $filename
        print $"Captured ($pane) to ($filename)"
    }
}

# Capture all panes to one file
def capture_all_to_one [output_file: string] {
    let panes = (tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index}' | lines)

    "" | save $output_file  # Create empty file

    for pane in $panes {
        $"=== ($pane) ===\n" | save --append $output_file
        tmux capture-pane -t $pane -p | save --append $output_file
        "\n" | save --append $output_file
    }

    print $"All panes captured to ($output_file)"
}

# Capture specific session
def capture_session [session: string] {
    let panes = (tmux list-panes -s $session -F '#{session_name}:#{window_index}.#{pane_index}' | lines)

    for pane in $panes {
        let filename = $"pane_($pane | str replace -a ':' '_' | str replace -a '.' '_').txt"
        tmux capture-pane -t $pane -p | save $filename
        print $"Captured ($pane) to ($filename)"
    }
}

# Capture with scrollback history
def capture_with_history [pane: string, lines: int = 3000] {
    let filename = $"pane_($pane | str replace -a ':' '_' | str replace -a '.' '_')_history.txt"
    tmux capture-pane -t $pane -S $"-($lines)" -p | save $filename
    print $"Captured ($pane) with ($lines) lines of history to ($filename)"
}

# Main function
def main [
    output: path # Path file containing tmux panes output
] {
    capture_all_to_one $output
}
 
