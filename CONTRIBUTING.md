# Contributing to Yves

You are more than welcomed to contribute for our project.

## Bugs reports and questions

If you see a bug, please open an [issue](https://github.com/frx-org/yves/issues/new/choose).

> [!IMPORTANT]
> If you find a bug with an AI assistance, please disclose it in the issue.

## Contributing

We use `uv` to manage dependencies.
So please use it to make sure we have the same working environment.

If you are using `nix` we provide a [`shell.nix`](./shell.nix) to get a whole working dev environment.

> [!IMPORTANT]
> If you contribute with an AI assistance, please disclose it in the pull request.

### Formatting and linting

We use [`ruff`](https://docs.astral.sh/ruff/) for formatting and linting in the CI.
Your code must respect that or else CI will fail.
For the documentation, we use [`numpydoc`](https://numpydoc.readthedocs.io/en/latest/format.html) style.

> [!TIP]
> If you have `just` and `nix` you can run `just format` to automatically format everything.

### Testing

We use [`pytest`](https://docs.pytest.org/en/stable/) to run unit tests in the CI.
You are invited to write tests for your code as often as possible.

> [!TIP]
> If you have `just` and `nix` you can run `just test` to automatically run every tests.
