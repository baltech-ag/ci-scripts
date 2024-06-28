#!/usr/bin/env python3

import re
import subprocess

from argparse import ArgumentParser, Namespace 
from pathlib import Path
from string import Template
from typing import Literal, NamedTuple, get_args as get_type_args


ReleaseMode = Literal["major", "minor", "patch"]
EventName = Literal["push", "create", "pull_request"]

_ZERO_PAD_PATTERN = re.compile(r"0\d")
_RELEASE_MODES = list(get_type_args(ReleaseMode))
_RELEASE_BRANCH_PATTERN = re.compile(rf"^release-(?P<mode>{'|'.join(_RELEASE_MODES)})(-(?P<project>\d\d\d\d))?$")


class ReleaseActionsError(Exception):
    pass


def _check_output(*commands: str) -> str:
    output = subprocess.check_output(commands).decode("utf-8")
    return output.strip() if output else ""


def _git(*commands: str) -> str:
    return _check_output("git", *commands)


def _increase_version(version: str, mode: ReleaseMode) -> str:
    parts = version.split(".")
    if mode == "major":
        next_parts = [int(parts[0]) + 1, 0, 0]
    elif mode == "minor":
        next_parts = [int(parts[0]), int(parts[1]) + 1, 0]
    elif mode == "patch":
        next_parts = [int(parts[0]), int(parts[1]), int(parts[2]) + 1]
    else:
        raise ReleaseActionsError(f"Unexpected mode '{mode}', expected one of "
                                  f"{'|'.join(_RELEASE_MODES)}")
    if any(_ZERO_PAD_PATTERN.match(parts[part]) for part in (1, 2)):
        return f"{next_parts[0]}.{next_parts[1]:02}.{next_parts[2]:02}"
    else:
        return f"{next_parts[0]}.{next_parts[1]}.{next_parts[2]}"


def _is_valid_release_branch(branch_name: str) -> bool:
    return bool(_RELEASE_BRANCH_PATTERN.match(branch_name))


def _get_base_branch() -> str:
    # HEAD points to the commit that updated the VERSION file a moment ago.
    # HEAD~1 (previous commit) must be used to determine the base branch.
    remote_base_branches = _git(
        "branch", '--remote',
        "--contains", "HEAD",
        '--format=%(refname:short)'
    ).split("\n")
    base_branches = [branch.removeprefix("origin/") for branch in remote_base_branches]
    release_branches = set(
        branch
        for branch in base_branches
        if _is_valid_release_branch(branch)
    )
    assert len(release_branches) == 1, \
        ("No release branch found that points to HEAD. "
         f"Branches pointing to HEAD: {', '.join(base_branches)}")
    for branch in base_branches:
        if branch == "master" or branch.startswith("v"):
            return branch
    else:
        raise ReleaseActionsError(f"Could not find base branch ('master' or 'v*') in "
                         f"possible branches: {', '.join(base_branches)}")


class ReleaseEvent(NamedTuple):
    deploy_mode: Literal["development", "release"]
    stage: Literal["branch-created", "pr-merged", "tag-created", "commit-pushed"]
    sub_project_id: str | None
    version: str


def print_release_context(args: Namespace) -> None:
    release_branch_pattern = "release-(?P<mode>[a-z]+)(-(?P<id>\d{4}))?"
    version_tag_pattern = "refs/tags/v((?P<id>\d{4})-)?(\d{1,2}.\d{1,2}.\d{1,2})"

    def _get_project_name(spid: str | None) -> str:
        if not spid:
            return args.repository_name

        try:
            return next(Path().glob(f"{sub_project_id}_*")).name
        except StopIteration:
            raise ReleaseActionsError(f"'{sub_project_id}' is not a valid project id in this repository!")


    def _get_version_file(spid: str | None) -> Path:
        if spid:
            return Path(f"{_get_project_name(spid)}/VERSION")
        return Path("VERSION")

    def _get_current_version(spid: str | None, *, required: bool = True) -> str:
        versionfile = _get_version_file(spid)
        if not versionfile.exists():
            if required:
                raise ReleaseActionsError(f"version file `{versionfile}` does not exists!")
            return ""
        return versionfile.read_text().strip()

    # create release branch
    if args.event == "create" and (match := re.match(rf"^refs/heads/{release_branch_pattern}$", args.ref)):
        sub_project_id = match.group("id")
        version = _increase_version(_get_current_version(sub_project_id), match.group("mode"))
        event = ReleaseEvent(
            deploy_mode="development",
            stage="branch-created",
            sub_project_id=sub_project_id,
            version=version,
        )

    # merge release PR
    elif args.event ==  "pull_request" and (match := re.match(rf"^{release_branch_pattern}$", args.ref)):
        sub_project_id = match.group("id")
        version = _get_current_version(sub_project_id)
        event = ReleaseEvent(
            deploy_mode="development",
            stage="pr-merged",
            sub_project_id=sub_project_id,
            version=version,
        )

    # push version tag
    elif args.event == "push" and (match:= re.match(rf"^{version_tag_pattern}$", args.ref)):
        sub_project_id = match.group("id")
        version = _get_current_version(sub_project_id)
        event = ReleaseEvent(
            deploy_mode="release",
            stage="tag-created",
            sub_project_id=sub_project_id,
            version=version,
        )

    # commit during development
    else:
        event = ReleaseEvent(
            deploy_mode="development",
            stage="commit-pushed",
            sub_project_id=None,
            version=_get_current_version(spid=None, required=False),
        )

    print(f"release-stage={event.stage}")
    print(f"deploy-mode={event.deploy_mode}")
    print(f"project-name={_get_project_name(event.sub_project_id)}")
    print(f"sub-project-id={event.sub_project_id or ''}")
    print(f"version={event.version}")
    print(f"version-file={_get_version_file(event.sub_project_id)}")

    tag = f"v{event.sub_project_id}-{event.version}" if event.sub_project_id else f"v{event.version}"
    print(f"tag={tag}")

    base_branch = _get_base_branch() if event.stage == "branch-created" else ""
    if event.sub_project_id and base_branch and event.sub_project_id not in base_branch:
        raise ReleaseActionsError(f"cannot release project {event.sub_project_id} on branch {base_branch}")
    print(f"base-branch={base_branch}")

    if args.jira_version_template:
        jira_version = Template(args.jira_version_template).substitute(projectid=event.sub_project_id, version=event.version)
    else:
        jira_version = tag
    print(f"jira-version={jira_version}")

def main() -> None:
    parser = ArgumentParser("Release Actions")
    subparsers = parser.add_subparsers(required=True)

    prepare_next_version_parser = subparsers.add_parser("print-release-context")
    prepare_next_version_parser.set_defaults(func=print_release_context)
    prepare_next_version_parser.add_argument("--event", choices=get_type_args(EventName), required=True)
    prepare_next_version_parser.add_argument("--repository-name", type=str, required=True)
    prepare_next_version_parser.add_argument("--ref", type=str, required=True)
    prepare_next_version_parser.add_argument("--jira-version-template", type=str, required=True)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
