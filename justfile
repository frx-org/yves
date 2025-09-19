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

# Build yves with uv
[group("yves")]
build:
    @uv build {{ yves }}

# Build yves with nix
[group("yves")]
nix-build:
    @nix-build {{ yves }} -A yves

# Build docker image
[group("yves")]
docker-build:
    @nix-build {{ yves }} -A docker.copyToDockerDaemon
    {{ yves }}/result/bin/copy-to-docker-daemon
    rm result

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

# Clean directory
[group("utils")]
clean:
    @rm -rf {{ yves }}/dist {{ yves }}/src/yves.egg-info {{ yves }}/result
