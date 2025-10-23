yves := justfile_directory()

[private]
default:
    @just --list --unsorted

[private]
py-check:
    @uv run ruff check
    @uv run ruff format --check
    @uv run basedpyright

[private]
py-format:
    @uv run ruff format

# Run pytest
[private]
pytest:
    @uv run pytest

# Build yves with uv
[group("yves")]
build:
    @uv build {{ yves }}

# Build yves with nix
[group("nix")]
nix-build:
    @nix-build {{ yves }} -A yves

# Run checks on codebase
[group("dev")]
check:
    @nix-shell {{ yves }}/shell.nix --command "just py-check"
    @nix-shell {{ yves }}/shell.nix --command "treefmt --ci"

# Format codebase
[group("dev")]
format:
    @nix-shell {{ yves }}/shell.nix --command "just py-format"
    @nix-shell {{ yves }}/shell.nix --command "treefmt"

# Run pytest
[group("dev")]
test:
    @nix-shell {{ yves }}/shell.nix --command "just pytest"

# Clean directory
[group("utils")]
clean:
    @rm -rf {{ yves }}/dist {{ yves }}/src/yves.egg-info {{ yves }}/result
