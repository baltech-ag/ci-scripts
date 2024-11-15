#!python3
# -*- coding: utf-8 -*-
import datetime
import json
import os
import sys
from argparse import ArgumentParser
from base64 import b64encode
from urllib import request
from urllib.error import HTTPError
from subprocess import check_call
from typing import Any, Optional, Dict


def _fail(msg: str) -> None:
    print(f"::error::{msg}" if os.environ.get("CI") else msg)
    sys.exit(1)


def _get_status_code(req: request.Request) -> int:
    try:
        return request.urlopen(req).status
    except HTTPError as e:
        return e.status


def _get_json(req: request.Request) -> Any:
    try:
        response = request.urlopen(req)
    except HTTPError:
        return None
    else:
        return json.loads(response.read())


def _assert_ok_status(req: request.Request) -> None:
    status = _get_status_code(req)
    if 200 <= status < 300:
        return
    _fail(f"request `{req.full_url}` failed with status code {status}")



class Jira:
    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url
        self.username = username
        self.password = password

    def add_attachment(self, issue: str, path: str) -> None:
        check_call([
            "curl", 
            "--user", f"{self.username}:{self.password}",
            "--request", "POST", 
            "--header", "X-Atlassian-Token: nocheck", # disable XSRF check
            "--form", f"file=@{os.path.abspath(path)}",
            f"{self.base_url}/rest/api/2/issue/{issue}/attachments",
        ])

    def add_comments(self, comments_file: str) -> None:
        with open(comments_file, mode='r') as cf:
            comments = json.load(cf)

        for issue, comment in comments.items():
            if isinstance(comment, dict):
                attachments = comment.get('attachments', [])
                comment = comment.get('comment', '')
            else:
                attachments = []
            for attachment in attachments:
                self.add_attachment(issue, attachment)
            self.add_comment(issue, comment)

    def add_comment(self, issue: str, comment: str) -> None:
        _assert_ok_status(
            self._request(
                f"issue/{issue}/comment",
                headers={"Content-Type": "application/json"},
                data=json.dumps({"body": comment}).encode(),
            )
        )

    def get_issue(self, issue: str) -> Any:
        return _get_json(self._request(f"issue/{issue}"))

    def get_version(self, project: str, version: str) -> Any:
        versions = _get_json(self._request(f"project/{project}/versions"))
        if versions:
            for version_data in versions:
                if version_data.get("name") == version:
                    return version_data

    def release_version(self, project: str, version: str) -> None:
        version_data = self.get_version(project, version)
        if version_data is None:
            _fail(f"version {version} in project {project} does not exist")

        _assert_ok_status(
            self._request(
                f"version/{version_data['id']}",
                method="PUT",
                headers={"Content-Type": "application/json"},
                data=json.dumps({
                    "released": True,
                    "releaseDate": datetime.date.today().strftime("%Y-%m-%d")
                }).encode()
            )
        )

    def _request(
            self,
            path: str,
            method: Optional[str] = None,
            headers: Optional[Dict[str, str]] = None,
            data: Optional[bytes] = None
    ) -> request.Request:
        login = f"{self.username}:{self.password}"
        return request.Request(
            f"{self.base_url}/rest/api/2/{path}",
            method=method,
            headers={
                "Authorization": "Basic " + b64encode(login.encode()).decode(),
                **(headers or {})
            },
            data=data
        )


if __name__ == "__main__":
    parser = ArgumentParser("JIRA")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    subparsers = parser.add_subparsers(required=True)

    add_comment_parser = subparsers.add_parser("add-comment")
    add_comment_parser.set_defaults(func=Jira.add_comment)
    add_comment_parser.add_argument("--issue", required=True)
    add_comment_parser.add_argument("--comment", required=True)

    add_attachments = subparsers.add_parser("add-attachment")
    add_attachments.set_defaults(func=Jira.add_attachment)
    add_attachments.add_argument("--issue", required=True)
    add_attachments.add_argument("--path", required=True)

    add_comments_parser = subparsers.add_parser("add-comments")
    add_comments_parser.set_defaults(func=Jira.add_comments)
    add_comments_parser.add_argument("--comments-file", required=True)

    get_issue_parser = subparsers.add_parser("get-issue")
    get_issue_parser.set_defaults(func=Jira.get_issue)
    get_issue_parser.add_argument("--issue", required=True)

    get_version_parser = subparsers.add_parser("get-version")
    get_version_parser.set_defaults(func=Jira.get_version)
    get_version_parser.add_argument("--project", required=True)
    get_version_parser.add_argument("--version", required=True)

    release_version_parser = subparsers.add_parser("release-version")
    release_version_parser.set_defaults(func=Jira.release_version)
    release_version_parser.add_argument("--project", required=True)
    release_version_parser.add_argument("--version", required=True)

    args = parser.parse_args().__dict__

    jira = Jira(
        base_url=args.pop("base_url"),
        username=args.pop("username"),
        password=args.pop("password"),
    )
    func = args.pop("func")
    result = func(jira, **args)
    if result is not None:
        print(json.dumps(result, indent=2))
