# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This directory holds global Python scripts — standalone utilities intended to be runnable from anywhere on the user's system, not tied to any single project.

## Environment

- A Python virtualenv is already activated globally in the user's shell. Do **not** create a new venv, run `python -m venv`, or prepend `source .../activate` to commands. Just invoke `python` / `pip` directly.
- Install dependencies with `uv pip install <pkg>` (the global `~/.venv` has no `pip` module — do not call `pip` or `python -m pip`). If a script grows real dependencies, add a `requirements.txt` at the repo root so the global env stays reproducible.

## Conventions for scripts here

- Every script must be **self-executable from anywhere** — no `.py` extension, no `python` prefix needed. Create them like:
  ```bash
  touch ~/.scripts/<name>
  chmod +x ~/.scripts/<name>
  ```
  Then invoke as just `<name>` from any directory (this dir is on `$PATH`).
- Start every script with `#!/usr/bin/env python3`.
- Every script **must** use `argparse` with:
  - A clear top-level `description=` summarizing what the script does.
  - `help=` text on every argument/flag.
  - Sensible defaults and `--` long flags where applicable.
  So `<name> --help` always prints useful usage.
- Scripts are global utilities — assume they may be invoked from any working directory. Resolve paths explicitly via args rather than relying on `cwd`.
- Not a package: don't add `__init__.py` or cross-script imports unless the user asks. Prefer duplication over premature shared modules.
- No git repo here yet — don't run `git init` unless asked.
