#!/usr/bin/env python3
"""Swap two strings in UTF-8 file contents and file names below a directory."""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path


def swap(value: str, first: str, second: str) -> str:
    """Swap first and second without letting replacements overlap."""
    marker = f"__STRING_SWAP_{uuid.uuid4().hex}__"
    while marker in value:
        marker = f"__STRING_SWAP_{uuid.uuid4().hex}__"
    return value.replace(first, marker).replace(second, first).replace(marker, second)


def files_below(root: Path) -> list[Path]:
    """Return regular files below root, excluding Git metadata and symlinks."""
    result: list[Path] = []
    for path in root.rglob("*"):
        if ".git" in path.relative_to(root).parts:
            continue
        if not path.is_symlink() and path.is_file():
            result.append(path)
    return result


def content_changes(
    files: list[Path], script: Path, first: str, second: str
) -> list[tuple[Path, bytes]]:
    """Prepare changed UTF-8 contents, leaving binary files untouched."""
    changes: list[tuple[Path, bytes]] = []
    for path in files:
        if path.resolve() == script:
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if first not in text and second not in text:
            continue
        changes.append((path, swap(text, first, second).encode("utf-8")))
    return changes


def rename_plan(
    files: list[Path], first: str, second: str
) -> list[tuple[Path, Path, Path]]:
    """Validate and return source, temporary, and destination file paths."""
    sources = [path for path in files if first in path.name or second in path.name]
    source_set = set(sources)
    destinations = [path.with_name(swap(path.name, first, second)) for path in sources]

    if len(destinations) != len(set(destinations)):
        raise FileExistsError("교환 결과에 중복되는 파일명이 있습니다.")
    for destination in destinations:
        if destination.exists() and destination not in source_set:
            raise FileExistsError(f"대상 파일이 이미 존재합니다: {destination}")

    plan: list[tuple[Path, Path, Path]] = []
    for source, destination in zip(sources, destinations, strict=True):
        temporary = source.with_name(f".{source.name}.swap-{uuid.uuid4().hex}")
        plan.append((source, temporary, destination))
    return plan


def rename_files(plan: list[tuple[Path, Path, Path]]) -> None:
    """Rename files through unique temporary names and roll back on failure."""
    staged: list[tuple[Path, Path, Path]] = []
    try:
        for source, temporary, destination in plan:
            source.rename(temporary)
            staged.append((source, temporary, destination))
    except Exception:
        for source, temporary, _ in reversed(staged):
            temporary.rename(source)
        raise

    completed: list[tuple[Path, Path, Path]] = []
    try:
        for source, temporary, destination in plan:
            temporary.rename(destination)
            completed.append((source, temporary, destination))
    except Exception:
        for _, temporary, destination in reversed(completed):
            destination.rename(temporary)
        for source, temporary, _ in reversed(plan):
            if temporary.exists():
                temporary.rename(source)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--first", default="문제1")
    parser.add_argument("--second", default="문제2")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.first or not args.second or args.first == args.second:
        print("서로 다른 비어 있지 않은 문자열을 지정해야 합니다.", file=sys.stderr)
        return 2

    root = args.root.resolve()
    if not root.is_dir():
        print(f"디렉터리가 아닙니다: {root}", file=sys.stderr)
        return 2

    files = files_below(root)
    changes = content_changes(files, Path(__file__).resolve(), args.first, args.second)
    plan = rename_plan(files, args.first, args.second)

    if args.dry_run:
        for path, _ in changes:
            print(f"내용: {path.relative_to(root)}")
        for source, _, destination in plan:
            print(f"파일명: {source.relative_to(root)} -> {destination.relative_to(root)}")
        print(f"내용 {len(changes)}개, 파일명 {len(plan)}개를 교환할 예정입니다.")
        return 0

    for path, data in changes:
        mode = path.stat().st_mode
        temporary = path.with_name(f".{path.name}.content-{uuid.uuid4().hex}")
        temporary.write_bytes(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    rename_files(plan)
    print(f"내용 {len(changes)}개, 파일명 {len(plan)}개를 교환했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
