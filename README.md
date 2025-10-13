# Yves

If you have already been in one of these situations:

- "What did you do today?", asked your favorite boss
- "Can you write me a report about what you did months ago and probably don't remember?", asked the same person
- "I'm so lazy to explain what I did today for the daily", you said

Meet Yves (also known as "**Y**our **V**aluable **E**fficient **S**ummarizer"), your personal assistant that will write a daily summary about what you did every day in a professional `markdown` report.

> [!WARNING]
> This is **highly experimental** as it is not done yet.
> You _will_ encounter bugs, please open an [issue](https://github.com/frx-org/yves/issues/new/choose) and remember to be polite.

> [!CAUTION]
> Remember that it is a **hobby project** and it first aims to solve _our_ problems.
> If submitted feature requests are considered relevant (which is purely subjective), we will make our best to implement them but note that we will take our time since we are definitely not paid for this.

## Usage

Yves will watch

- Directories on your file system to check changes (addition/deletion/modification)
- [`tmux`](https://github.com/tmux/tmux) for commands and outputs

And will send these to a LLM that will write the report.

> [!NOTE]
> As you can see, the data will stay on your computer until it reaches your chosen LLM provider.
> We do not collect nor store any of your information.

### Requirements

- `tmux` is optional but is recommended to give more insights to the LLM
- LLM provider (_e.g._ Mistral AI, OpenAI, Anthropic, ...)
- One of the following to build the binary
  - [UV](https://docs.astral.sh/uv/)
  - [Nix](https://nixos.org/)
- [`just`](https://just.systems/) to easily run commands (_optional_)

### Build

You can create a virtual environment with `uv`

```bash
uv sync
```

which will produce the `yves` binary that will be added into your `$PATH`.

### Using Nix

#### Build the binary

We use [`uv2nix`](https://github.com/pyproject-nix/uv2nix) to build the project with `nix`

```bash
nix-build -A yves
```

which will produce the `yves` binary in `result/bin/yves`.

#### Using the `home-manager` module

If you use [`home-manager`](https://github.com/nix-community/home-manager), we provide a module for you to load it.

This will:

- Create a `systemd` user service that will automatically start `yves` in a watching mode: you can check the status with `systemctl --user status yves.service`
- Install the `yves` package

```nix
{ pkgs, ...}:

{
  imports = [ (import "${./path/to/yves/src}/default.nix" { inherit pkgs; }).homeModules.default ]

  services.yves = {
    enable = true;
  };
}
```

> [!NOTE]
> `./path/to/yves/src` must point to the `yves` source directory.
> You can achieve this with your favorite fetcher, using Flakes, [`niv`](https://github.com/nmattia/niv), [`npins`](https://github.com/andir/npins), etc.

> [!TIP]
> If you use the `home-manager` module you do not have to manually build the package since it will be done for you!

### Run

In general, you can call your favorite assistant by calling their name _i.e._

```bash
yves
```

By default if you just call Yves, they will provide you information about how to work with them (_i.e._ help page).
You can give directives to them for your specific needs (_i.e._ subcommands).

#### Initialize configuration file

> [!TIP]
> This is recommended when you first use Yves!

Run

```bash
yves init
```

to interactively configure your personal assistant.
After that you can finetune your configuration file (see [Configuration](#configuration)).

#### Check everything is correctly set

> [!TIP]
> This is recommended just after you initialized your configuration file!

Run

```bash
yves check
```

If you don't see any errors, you are good to go!

#### Watch and summarize

Call your personal assistant to record your steps (this is the main subcommand).

```bash
yves record
```

> [!NOTE]
> If you use the `systemd` user service, this is automatically done but remember to restart the service after configuring Yves!

### Global arguments

These flags can be used for any subcommands.

| Argument        | Type   | Default                 | Description                |
| --------------- | ------ | ----------------------- | -------------------------- |
| `--config`/`-c` | `str`  | `~/.config/yves/config` | Path to configuration file |
| `--debug`       | `bool` | `False`                 | Set logging level to debug |

## Configuration

You can configure your assistant with the configuration file (default path is `~/.config/yves/config`).
It will be automatically created when you first call Yves.

This is an example configuration

```
[filesystem]
dirs = ~/work/yves, /persist/my/other/project
output_file = ~/.local/state/yves/fs_changes.json
include_filetypes = .py, .nix
exclude_filetypes = .pyc, .git
major_changes_only = False
min_lines_changed = 3
similarity_threshold = 0.7

[tmux]
panes =
output_file = ~/.local/state/yves/tmux_changes.json
capture_full_output = False

[llm]
api_key =
model_name = gpt-4
provider = github_copilot

[summarizer]
output_dir = ~/.local/share/yves
token_limit = 30000
at = 17:00
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

LiteLLM uses the following format `{provider}/{model_name}`.
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

## Contributing

Please refer to [CONTRIBUTING.md](/CONTRIBUTING.md).

## Have any questions?

If you have any questions regarding the project or its usage you can also post an issue.
We will open GitHub discussions later if the community becomes bigger but for now we consider issues are enough.
