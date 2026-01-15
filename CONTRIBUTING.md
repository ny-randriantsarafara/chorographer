# Contributing to Chorographer

Thanks for your interest in contributing. This guide keeps contributions consistent and easy to review.

## Ways to contribute

- Report a bug or request a feature via GitHub Issues.
- Improve documentation.
- Submit a pull request with fixes or enhancements.

## Before you start

- Check existing issues and pull requests to avoid duplication.
- For larger changes, open an issue first to discuss scope and approach.

## Development setup

```bash
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

## Pull request workflow

1. Fork the repository and create a feature branch:
   `git checkout -b feat/your-change`
2. Make focused commits with clear messages.
3. Ensure tests pass locally.
4. Open a pull request describing what changed and why.

## Coding guidelines

- Keep changes focused and avoid unrelated refactors.
- Add or update tests when behavior changes.
- Update documentation when relevant.

## Reporting issues

Please include:

- Steps to reproduce
- Expected vs. actual behavior
- Relevant logs or error messages
- Environment details (OS, Python version)
