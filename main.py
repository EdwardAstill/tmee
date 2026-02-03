#!/usr/bin/env python3
"""
Recursive folder tree printer CLI.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Filters:
    show_hidden: bool  # Renamed for clarity: default will be True
    dirs_only: bool
    pattern: str | None
    ignore_names: tuple[str, ...]
    ignore_globs: tuple[str, ...]


def is_hidden(path: Path) -> bool:
    return path.name.startswith(".")


def matches_any_glob(name: str, globs: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(name, g) for g in globs)


def should_ignore(path: Path, flt: Filters) -> bool:
    name = path.name
    # Logic flipped: if we should NOT show hidden and it IS hidden, ignore it.
    if not flt.show_hidden and is_hidden(path):
        return True
    if name in flt.ignore_names:
        return True
    if matches_any_glob(name, flt.ignore_globs):
        return True
    if flt.pattern and not fnmatch.fnmatch(name, flt.pattern):
        return True
    if flt.dirs_only and not path.is_dir():
        return True
    return False


def safe_scandir(dir_path: Path):
    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                yield entry
    except PermissionError:
        return
    except FileNotFoundError:
        return


def tree(
    root: Path,
    flt: Filters,
    max_depth: int | None,
    follow_symlinks: bool,
) -> list[str]:
    lines: list[str] = []
    seen_dirs: set[tuple[int, int]] = set()
    seen_realpaths: set[str] = set()

    def mark_seen(p: Path) -> bool:
        try:
            st = p.stat()
            key = (getattr(st, "st_dev", -1), getattr(st, "st_ino", -1))
            if key != (-1, -1):
                if key in seen_dirs:
                    return True
                seen_dirs.add(key)
                return False
        except OSError:
            pass

        rp = str(p.resolve())
        if rp in seen_realpaths:
            return True
        seen_realpaths.add(rp)
        return False

    def walk(dir_path: Path, prefix: str, depth: int) -> None:
        if max_depth is not None and depth > max_depth:
            return

        entries = []
        for e in safe_scandir(dir_path):
            p = Path(e.path)
            try:
                is_dir = e.is_dir(follow_symlinks=follow_symlinks)
            except OSError:
                is_dir = False
            entries.append((p, is_dir))

        entries.sort(key=lambda x: (not x[1], x[0].name.lower()))
        entries = [(p, is_dir) for (p, is_dir) in entries if not should_ignore(p, flt)]

        for idx, (p, is_dir) in enumerate(entries):
            last = idx == len(entries) - 1
            branch = "└── " if last else "├── "
            lines.append(prefix + branch + p.name + ("/" if is_dir else ""))

            if is_dir:
                if follow_symlinks and mark_seen(p):
                    lines.append(prefix + ("    " if last else "│   ") + "↩︎ (cycle)")
                    continue
                extension = "    " if last else "│   "
                walk(p, prefix + extension, depth + 1)

    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {root}")

    lines.append(str(root) + "/")
    if follow_symlinks:
        mark_seen(root)
    walk(root, prefix="", depth=1)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Print a recursive directory tree.")
    ap.add_argument("path", nargs="?", default=".", help="Root folder (default: current dir).")
    ap.add_argument("--max-depth", type=int, default=None, help="Limit recursion depth.")
    
    # --- CHANGED HERE ---
    # We use action="store_false" so that if the flag is present, show_hidden becomes False.
    # We set dest="show_hidden" so it maps cleanly to our dataclass.
    ap.add_argument("--hide-dot", action="store_false", dest="show_hidden", help="Hide hidden files/folders (starting with .)")
    # --------------------

    ap.add_argument("--dirs-only", action="store_true", help="Show directories only.")
    ap.add_argument("--pattern", default=None, help='Only include names matching a glob, e.g. "*.pdf".')
    ap.add_argument("--ignore", action="append", default=[], help="Ignore exact name (repeatable).")
    ap.add_argument("--ignore-glob", action="append", default=[], help="Ignore glob (repeatable).")
    ap.add_argument("--follow-symlinks", action="store_true", help="Follow directory symlinks (cycle-safe).")
    args = ap.parse_args()

    flt = Filters(
        show_hidden=args.show_hidden, # This will be True unless --hide-dot is used
        dirs_only=args.dirs_only,
        pattern=args.pattern,
        ignore_names=tuple(args.ignore),
        ignore_globs=tuple(args.ignore_glob),
    )

    try:
        lines = tree(
            root=Path(args.path),
            flt=flt,
            max_depth=args.max_depth,
            follow_symlinks=args.follow_symlinks,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())