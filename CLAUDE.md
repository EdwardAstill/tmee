# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

tmee is a Python CLI tool that recursively prints directory tree structures. Single-module project (`main.py`), no external dependencies — uses only the Python standard library. Requires Python 3.8+.

## Build & Install

```bash
# Install from source (editable)
pip install -e .

# Install via uv (as documented in README)
uv tool install git+https://github.com/EdwardAstill/tmee.git

# Run directly
python main.py [path] [options]
```

Entry point: `tmee` command maps to `main:main` (configured in pyproject.toml).

No test suite, linter, or CI pipeline exists.

## Architecture

Everything lives in `main.py` (~189 lines):

- **`Filters` dataclass** — holds all filtering options (hidden files, dirs-only, glob patterns, ignore lists)
- **`tree(root, flt, max_depth, follow_symlinks)`** — recursive depth-first traversal with cycle-safe symlink following (tracks inodes + resolved paths), outputs formatted tree lines using box-drawing characters (├──, └──, │). Sorts directories first, then alphabetical case-insensitive.
- **`main()`** — argparse CLI entry point, builds Filters, calls tree(), optionally copies output to clipboard

Clipboard integration is platform-specific: `clip.exe` (Windows), `pbcopy` (macOS), `xclip -selection clipboard` (Linux).
