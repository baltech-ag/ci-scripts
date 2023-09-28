#!/usr/bin/env python3

import os
import re
import subprocess

from argparse import ArgumentParser, Namespace 
from pathlib import Path


_ROOT_PATH = Path(__file__).parent.parent
_VERSION_PATH = (_ROOT_PATH / "VERSION")
_ZERO_PAD_PATTERN = re.compile(r"0\d")


def check_output(*commands: str) -> str:
    output = subprocess.check_output(commands).decode("utf-8")
    return output.strip() if output else ""


def git(*commands: str) -> str:
    return check_output("git", *commands)


def tox(*commands: str) -> str:
    return check_output("tox", "--quiet", "--quiet", "--", *commands)


def increase_version(version: str, mode: str) -> str:
    parts = version.split(".")
    if mode == "major":
        next_parts = [int(parts[0]) + 1, 0, 0]
    elif mode == "minor":
        next_parts = [int(parts[0]), int(parts[1]) + 1, 0]
    elif mode == "patch":
        next_parts = [int(parts[0]), int(parts[1]), int(parts[2]) + 1]
    else:
        raise NotImplementedError(f"Unexpected mode '{mode}', expected one of "
                                  f"major|minor|patch")
    if any(_ZERO_PAD_PATTERN.match(parts[part]) for part in (1, 2)):
        return f"{next_parts[0]}.{next_parts[1]:02}.{next_parts[2]:02}"
    else:
        return f"{next_parts[0]}.{next_parts[1]}.{next_parts[2]}"


def prepare_next_version(args: Namespace) -> None:
    project = os.environ['CI_PROJECT_NAME']
    branch = os.environ['CI_BRANCH_NAME']
    assert branch in ("release-major", "release-minor", "release-patch")
    version = _VERSION_PATH.read_text().strip()
    next_version = increase_version(version, branch.removeprefix("release-"))
    _VERSION_PATH.write_text(next_version)
    git("add", str(_VERSION_PATH.resolve()))
    modified_files = tox("apply-version")
    for modified_file in modified_files.split("\n"):
        git("add", modified_file)
    git("commit", "-m", f"[release] {project} {next_version}")
    git("push", "origin", branch)


def create_release_branch(args: Namespace) -> None:
    version = _VERSION_PATH.read_text().strip()
    major_minor, patch = version.rsplit(".", 1)
    if int(patch) == 0:
        branch_name = "v" + str(major_minor)
        git("branch", branch_name)
        git("push", "origin", branch_name)


def main() -> None:
    parser = ArgumentParser("Release Actions")
    subparsers = parser.add_subparsers(required=True)

    prepare_next_version_parser = subparsers.add_parser("prepare-next-version")
    prepare_next_version_parser.set_defaults(func=prepare_next_version)

    create_release_branch_parser = subparsers.add_parser("create-release-branch")
    create_release_branch_parser.set_defaults(func=create_release_branch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
