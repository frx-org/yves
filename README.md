# Yves

If you have already been in one of these situations:

- "What did you do today?", asked your favorite boss
- "Can you write me a report about what you did months ago and probably don't remember?", asked the same person
- "I'm so lazy to explain what I did today for the daily", you said

Meet Yves (also known as "**Y**our **V**aluable **E**fficient **S**ummarizer"), your personal assistant that will write a daily summary about what you did every day in a professional `markdown` report.

> [!WARNING]
> This is **highly experimental** as it is not done yet.
> You _will_ encounter bugs, please open an [issue](https://github.com/rxfremk/yves/issues/new/choose) and remember to be polite.

> [!CAUTION]
> This is a private repository: if we gave you an access it means that we trust you so do not steal or leak the code and be respectful with everyone.
> Remember that it is a **hobby project** and it first aims to solve _our_ problems.
> If submitted feature requests are considered relevant (which is purely subjective), we will make our best to implement them but note that we will take our time since we are definitely not paid.
>
> We will revoke access if we see disrespectful behaviors regarding the project and its users.

## Usage

Yves will watch

- Directories on your file system to check changes (addition/deletion/modification)
- [tmux](https://github.com/tmux/tmux) for commands and outputs

And will send these to a LLM that will write the report.

> [!NOTE]
> As you can see, the data will stay on your computer until it reaches your chosen LLM provider.
> We do not collect nor store any of your information.

### Requirements

- `tmux` is optional but is recommended to give more insights to the LLM
- LLM provider (_e.g._ Mistral AI, OpenAI, Anthropic, ...)

### Build

#### Using `uv`

You can create a virtual environment with `uv`

```bash
uv sync
```

which will produce the `yves` binary that will be added into your `$PATH`.

#### Using `nix`

We use [uv2nix](https://github.com/pyproject-nix/uv2nix) to build the project with `nix`

```bash
nix-build
```

which will produce the `yves` binary in `result/bin/yves`.

### Run

Just call your favorite assistant with `yves`

| Argument        | Type   | Default                 | Description                |
| --------------- | ------ | ----------------------- | -------------------------- |
| `--config`/`-c` | `str`  | `~/.config/yves/config` | Path to configuration file |
| `--debug`       | `bool` | `False`                 | Set logging level to debug |

## Configuration

You can configure your assistant with the configuration file (default path is `~/.config/yves/config`).
It will be automatically created when you first call Yves.

This is the default configuration

```
[filesystem]
dirs =
output_file = ~/.local/state/yves/fs_changes.json
include_filetypes =
exclude_filetypes =
major_changes_only = False
min_lines_changed = 3
similarity_threshold = 0.7

[tmux]
panes =
output_file = ~/.local/state/yves/tmux_changes.json
capture_full_output = False

[llm]
api_key =
model_name = # mandatory
provider = # mandatory

[summarizer]
output_dir = ~/.local/share/yves
token_limit = 30000
at = 19:00
```

### File system

You must set directories to `dirs` variable (split by commas).

> [!WARNING]
> We **highly** recommend to set `include_filetypes` or `exclude_filetypes`, especially if you have huge directories as the searching can be slow.

### Tmux

You can specify specific panes you want to watch with `panes` (split by commas) with the following format `session:window.pane`.

> [!TIP]
> You can leave it as empty and it will watch every Tmux panes, which is generally what you want.

### LLM provider

We use [LiteLLM](https://docs.litellm.ai/) to support LLM providers.
If it is supported by this, it will probably be supported by Yves.

LiteLLM follows the following format `{provider}/{model_name}`.
So if you take [OpenAI](https://docs.litellm.ai/docs/providers/openai) example, your configuration should look like this

```
[llm]
api_key = PRIVATE_KEY
model_name = gpt-4o-mini
provider = openai
```

> [!WARNING]
> We only tested with [OpenAI](https://docs.litellm.ai/docs/providers/openai) and [GitHub Copilot](https://docs.litellm.ai/docs/providers/github_copilot).
> Hence we highly encourage you to share your experience with other LLM providers.

### Summarizer

Yves will write a report for you everyday and only once (_i.e._ you cannot arbitrarily choose specific days or multiple time reports per day).
You can provide the summary time with the field `at` with the following format `%H:%M` (_i.e._ 24-hour format).

## Development

This project is written in Python and use [uv](https://docs.astral.sh/uv/) for package management.

To improve reproducibility, we use Nix where `shell.nix` exposes the packages we use for development.
