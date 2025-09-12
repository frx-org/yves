yves := justfile_directory()

[private]
default:
    @just --list --unsorted

[private]
py-check:
    @uv run ruff check
    @uv run ruff format --check

[private]
py-format:
    @uv run ruff format

# Run pytest
[private]
pytest:
    @uv run pytest

# Run checks on codebase
[group("dev")]
check:
    @nix-shell {{ yves }}/shell.nix --command "just py-check"

# Format codebase
[group("dev")]
format:
    @nix-shell {{ yves }}/shell.nix --command "just py-format"
    @nix-shell {{ yves }}/shell.nix --command "treefmt"

# Run pytest
[group("dev")]
test:
    @nix-shell {{ yves }}/shell.nix --command "just pytest"
