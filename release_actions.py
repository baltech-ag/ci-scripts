#!/usr/bin/env python3

import os
import re
import subprocess

from argparse import ArgumentParser, Namespace 
from pathlib import Path


_ROOT_PATH = Path(__file__).parent.parent
_VERSION_PATH = (_ROOT_PATH / "VERSION")
_ZERO_PAD_PATTERN = re.compile(r"0\d")
_RELEASE_BRANCHES = ("release-major", "release-minor", "release-patch")


def check_output(*commands: str) -> str:
    output = subprocess.check_output(commands).decode("utf-8")
    return output.strip() if output else ""


def git(*commands: str) -> str:
    return check_output("git", *commands)


def tox(*commands: str) -> str:
    return check_output("tox", "-v", "-v", "--", *commands)


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


def print_base_branch(args: Namespace) -> None:
    # HEAD points to the commit that updated the VERSION file a moment ago.
    # HEAD~1 (previous commit) must be used to determine the base branch.
    remote_base_branches = git("branch", '--remote',
                               "--contains", "HEAD~1",
                               '--format=%(refname:short)').split("\n")
    base_branches = [branch.removeprefix("origin/") for branch
                     in remote_base_branches]
    assert len(set(_RELEASE_BRANCHES) & set(base_branches)) == 1, \
        (f"No release branch ({', '.join(_RELEASE_BRANCHES)}) found that "
         f"points to HEAD. Branches pointing to HEAD: "
         f"{', '.join(base_branches)}")
    for branch in base_branches:
        if branch == "master" or branch.startswith("v"):
            print(branch, end="")
            break
    else:
        raise ValueError(f"Could not find base branch ('master' or 'v*') in "
                         f"possible branches: {', '.join(base_branches)}")


def prepare_next_version(args: Namespace) -> None:
    project = os.environ['CI_PROJECT_NAME']
    branch = os.environ['CI_BRANCH_NAME']
    assert branch in _RELEASE_BRANCHES
    version = _VERSION_PATH.read_text().strip()
    next_version = increase_version(version, branch.removeprefix("release-"))
    print(f"Increasing version in {_VERSION_PATH} to {next_version}")
    _VERSION_PATH.write_text(next_version)
    tox("apply-version")
    # This ci-scripts repo is checked out at the root of the project for which
    # we are creating a new release ($PROJECT_ROOT/ci-scripts/). When git-adding
    # all files that were changed by apply-version, we need to exclude it.
    git("add", "--all", "--", ":(exclude)ci-scripts/*")
    git("commit", "-m", f"[release] {project} {next_version}")
    git("push", "origin", branch)


def main() -> None:
    parser = ArgumentParser("Release Actions")
    subparsers = parser.add_subparsers(required=True)

    print_base_branch_parser = subparsers.add_parser("print-base-branch")
    print_base_branch_parser.set_defaults(func=print_base_branch)

    prepare_next_version_parser = subparsers.add_parser("prepare-next-version")
    prepare_next_version_parser.set_defaults(func=prepare_next_version)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
