#!python3
# -*- coding: utf-8 -*-
import datetime
import json
import os
import sys
from argparse import ArgumentParser
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
    except HTTPError as e:
        print(f"::warning::request `{req.full_url}` failed with status code {e.status}" if os.environ.get("CI") else f"WARNING: request `{req.full_url}` failed with status code {e.status}")
        return None
    else:
        return json.loads(response.read())


def _assert_ok_status(req: request.Request) -> None:
    status = _get_status_code(req)
    if 200 <= status < 300:
        return
    _fail(f"request `{req.full_url}` failed with status code {status}")


class YouTrack:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip('/')
        self.token = token

    def add_attachment(self, issue: str, path: str) -> None:
        check_call([
            "curl",
            "--header", f"Authorization: Bearer {self.token}",
            "--request", "POST",
            "--form", f"file=@{os.path.abspath(path)}",
            f"{self.base_url}/api/issues/{issue}/attachments",
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
        req = self._request(
            f"api/issues/{issue}/comments",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"text": comment}).encode(),
        )
        status_code = _get_status_code(req)
        if status_code == 404:
            print(f"::warning::issue {issue} not found, skipping comment")
            return
        if 200 <= status_code < 300:
            return
        _fail(f"request `{req.full_url}` failed with status code {status_code}")

    def get_issue(self, issue: str) -> Any:
        return _get_json(self._request(f"api/issues/{issue}?fields=idReadable"))

    def get_fix_version_bundle_id(self, project: str) -> Optional[str]:
        """Auto-discover the bundle ID for the 'Fix versions' field from project settings."""
        fields = _get_json(self._request(
            f"api/admin/projects/{project}/customFields?fields=field(name),bundle(id)"
        ))
        if fields:
            for field in fields:
                field_info = field.get("field", {})
                if field_info.get("name") == "Fix versions":
                    bundle = field.get("bundle")
                    if bundle:
                        return bundle.get("id")
        return None

    def get_version(self, project: str, version: str) -> Any:
        """Get version info by looking up the bundle from project's Fix versions field."""
        bundle_id = self.get_fix_version_bundle_id(project)
        if not bundle_id:
            return None

        versions = _get_json(self._request(
            f"api/admin/customFieldSettings/bundles/version/{bundle_id}/values?$top=-1"
        ))
        if versions:
            for version_data in versions:
                if version_data.get("name") == version:
                    return version_data
        return None

    def release_version(self, project: str, version: str) -> None:
        bundle_id = self.get_fix_version_bundle_id(project)
        if not bundle_id:
            _fail(f"could not find Fix versions bundle for project {project}")

        version_data = self.get_version(project, version)
        if version_data is None:
            _fail(f"version {version} in project {project} does not exist")

        release_date_ms = int(datetime.datetime.now().timestamp() * 1000)
        _assert_ok_status(
            self._request(
                f"api/admin/customFieldSettings/bundles/version/{bundle_id}/values/{version_data['id']}",
                method="POST",
                headers={"Content-Type": "application/json"},
                data=json.dumps({
                    "released": True,
                    "releaseDate": release_date_ms
                }).encode()
            )
        )

    def close_issue(self, issue: str, state: str = "Closed") -> None:
        """Close an issue using YouTrack commands API."""
        _assert_ok_status(
            self._request(
                "api/commands",
                method="POST",
                headers={"Content-Type": "application/json"},
                data=json.dumps({
                    "query": f"State {state}",
                    "issues": [{"idReadable": issue}],
                    "silent": True
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
        return request.Request(
            f"{self.base_url}/{path}",
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                **(headers or {})
            },
            data=data
        )


if __name__ == "__main__":
    parser = ArgumentParser("YouTrack")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", required=True)
    subparsers = parser.add_subparsers(required=True)

    add_comment_parser = subparsers.add_parser("add-comment")
    add_comment_parser.set_defaults(func=YouTrack.add_comment)
    add_comment_parser.add_argument("--issue", required=True)
    add_comment_parser.add_argument("--comment", required=True)

    add_attachments = subparsers.add_parser("add-attachment")
    add_attachments.set_defaults(func=YouTrack.add_attachment)
    add_attachments.add_argument("--issue", required=True)
    add_attachments.add_argument("--path", required=True)

    add_comments_parser = subparsers.add_parser("add-comments")
    add_comments_parser.set_defaults(func=YouTrack.add_comments)
    add_comments_parser.add_argument("--comments-file", required=True)

    get_issue_parser = subparsers.add_parser("get-issue")
    get_issue_parser.set_defaults(func=YouTrack.get_issue)
    get_issue_parser.add_argument("--issue", required=True)

    get_version_parser = subparsers.add_parser("get-version")
    get_version_parser.set_defaults(func=YouTrack.get_version)
    get_version_parser.add_argument("--project", required=True)
    get_version_parser.add_argument("--version", required=True)

    release_version_parser = subparsers.add_parser("release-version")
    release_version_parser.set_defaults(func=YouTrack.release_version)
    release_version_parser.add_argument("--project", required=True)
    release_version_parser.add_argument("--version", required=True)

    close_issue_parser = subparsers.add_parser("close-issue")
    close_issue_parser.set_defaults(func=YouTrack.close_issue)
    close_issue_parser.add_argument("--issue", required=True)
    close_issue_parser.add_argument("--state", default="Closed")

    args = parser.parse_args().__dict__

    youtrack = YouTrack(
        base_url=args.pop("base_url"),
        token=args.pop("token"),
    )
    func = args.pop("func")
    result = func(youtrack, **args)
    if result is not None:
        print(json.dumps(result, indent=2))
