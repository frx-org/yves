# recapify

## Requirements

You need to use [tmux](https://github.com/tmux/tmux) when working on your projects to be able to extract your terminal outputs and make the summary.

## Development

This project is written in Python and use [uv](https://docs.astral.sh/uv/) for package management.

To improve reproducibility, we use Nix where `shell.nix` exposes the packages we use for development.
