#!python3
# -*- coding: utf-8 -*-
import datetime
import json
import os
import sys
from argparse import ArgumentParser
from urllib import request
from urllib.error import HTTPError
from urllib.parse import quote
from subprocess import check_call
from typing import Any, Optional, Dict, Tuple


_LINK_TYPE_MAP: Dict[str, Tuple[str, str]] = {
    "depends-on":       ("Depend",  "OUTWARD"),
    "is-required-for":  ("Depend",  "INWARD"),
    "relates-to":       ("Relate",  "BOTH"),
    "parent-for":       ("Subtask", "INWARD"),
    "subtask-of":       ("Subtask", "OUTWARD"),
}

_RESOLUTION_MAP: Dict[str, str] = {
    "done":                "Closed (Done)",
    "wont-do":             "Closed (Won't Do)",
    "duplicate":           "Closed (Duplicate)",
    "no-action-required":  "Closed (No Action Required)",
    "cannot-reproduce":    "Closed (Cannot Reproduce)",
}


def _fail(msg: str) -> None:
    print(f"::error::{msg}" if os.environ.get("CI") else msg, file=sys.stderr)
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
        body = e.read().decode() if e.readable() else ""
        print(f"::warning::request `{req.full_url}` failed with status code {e.status}: {body}" if os.environ.get("CI") else f"WARNING: request `{req.full_url}` failed with status code {e.status}: {body}", file=sys.stderr)
        return None
    else:
        return json.loads(response.read())


def _assert_ok_status(req: request.Request) -> None:
    try:
        response = request.urlopen(req)
        if 200 <= response.status < 300:
            return
        _fail(f"request `{req.full_url}` failed with status code {response.status}")
    except HTTPError as e:
        body = e.read().decode() if e.readable() else ""
        _fail(f"request `{req.full_url}` failed with status code {e.status}: {body}")


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
            print(f"::warning::issue {issue} not found, skipping comment", file=sys.stderr)
            return
        if 200 <= status_code < 300:
            return
        _fail(f"request `{req.full_url}` failed with status code {status_code}")

    def get_issue(self, issue: str) -> Any:
        return _get_json(self._request(f"api/issues/{issue}?fields=id,idReadable"))

    def get_fix_version_bundle_id(self, project: str) -> Optional[str]:
        """Auto-discover the bundle ID for the 'Fix versions' field from project settings."""
        issues = _get_json(self._request(
            f"api/issues?query=project:{project}&fields=customFields(name,projectCustomField(bundle(id)))&$top=1"
        ))
        if issues:
            for field in issues[0].get("customFields", []):
                if field.get("name") == "Fix versions":
                    bundle = field.get("projectCustomField", {}).get("bundle")
                    if bundle:
                        return bundle.get("id")
        return None

    def get_version(self, project: str, version: str) -> Any:
        """Get version info by looking up the bundle from project's Fix versions field."""
        bundle_id = self.get_fix_version_bundle_id(project)
        if not bundle_id:
            return None

        versions = _get_json(self._request(
            f"api/admin/customFieldSettings/bundles/version/{bundle_id}/values?fields=id,name&$top=-1"
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

    def get_user(self, login: str) -> Optional[Dict]:
        """Get a YouTrack user by login."""
        return _get_json(self._request(
            f"api/users/{quote(login)}?fields=id,login"
        ))

    def search_issues(self, project: str, summary: str) -> Optional[Dict]:
        """Search for an issue by exact summary in a project."""
        query = quote(f'project: {{{project}}} summary: {summary}')
        issues = _get_json(self._request(
            f"api/issues?query={query}&fields=idReadable,summary&$top=10"
        ))
        if issues:
            for issue in issues:
                if issue.get("summary") == summary:
                    return {"idReadable": issue["idReadable"]}
        return None

    def issue_create(self, project: str, summary: str, description: str = "",
                     issue_type: str = "", tags: str = "",
                     assignee: str = "", deduplicate: bool = False) -> Dict:
        """Create a YouTrack issue with optional deduplication."""
        if deduplicate:
            existing = self.search_issues(project, summary)
            if existing:
                return existing

        custom_fields = []
        if issue_type:
            custom_fields.append({
                "name": "Type",
                "$type": "SingleEnumIssueCustomField",
                "value": {"name": issue_type}
            })
        if assignee:
            user = self.get_user(assignee)
            if not user:
                _fail(f"user with login {assignee} not found")
            custom_fields.append({
                "name": "Assignee",
                "$type": "SingleUserIssueCustomField",
                "value": {"id": user["id"]}
            })

        body: Dict = {
            "project": {"shortName": project},
            "summary": summary,
            "description": description,
            "customFields": custom_fields,
        }
        if tags:
            tag_ids = self.get_tag_ids()
            body["tags"] = [{"id": tag_ids[t.strip()]} for t in tags.split(",")]

        result = _get_json(self._request(
            "api/issues?fields=idReadable",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=json.dumps(body).encode()
        ))
        if not result:
            _fail("failed to create issue")
        return result

    def get_tag_ids(self) -> Dict[str, str]:
        """Get all issue tags as {name: id} map."""
        tags = _get_json(self._request(
            "api/issueTags?fields=id,name&$top=-1"
        ))
        if not tags:
            _fail("failed to retrieve issue tags")
        return {t["name"]: t["id"] for t in tags}
    
    def issue_watch(self, issue: str, logins: str) -> None:
        """Add watchers to an issue by logins (comma-separated)."""
        for login in logins.split(","):
            login = login.strip()
            if not login:
                continue
            user = self.get_user(login)
            if not user:
                _fail(f"user with login {login} not found")
            _assert_ok_status(self._request(
                f"api/issues/{issue}/watchers",
                method="POST",
                headers={"Content-Type": "application/json"},
                data=json.dumps({"id": user["id"]}).encode()
            ))

    def get_link_type_ids(self) -> Dict[str, str]:
        """Get all issue link types as {name: id} map."""
        link_types = _get_json(self._request(
            "api/issueLinkTypes?fields=id,name"
        ))
        if not link_types:
            _fail("failed to retrieve issue link types")
        return {lt["name"]: lt["id"] for lt in link_types}

    def issue_link(self, issue: str, link_type: str, links: str) -> None:
        """Link an issue to other issues."""
        yt_name, direction = _LINK_TYPE_MAP[link_type]
        link_type_id = self.get_link_type_ids()[yt_name]
        # Direction suffix: added issues go on opposite side
        # OUTWARD = {issue} -> {links}, so links are targets (t)
        # INWARD = {links} -> {issue}, so links are sources (s)
        dir_suffix = {"OUTWARD": "t", "INWARD": "s", "BOTH": ""}[direction]

        for target in links.split(","):
            target = target.strip()
            if not target:
                continue
            # Resolve target issue database ID
            target_issue = self.get_issue(target)
            if not target_issue:
                _fail(f"issue {target} not found")
            _assert_ok_status(self._request(
                f"api/issues/{issue}/links/{link_type_id}{dir_suffix}/issues",
                method="POST",
                headers={"Content-Type": "application/json"},
                data=json.dumps({"id": target_issue["id"]}).encode()
            ))

    def close_issue(self, issue: str, state: str = "Closed (Done)") -> None:
        """Close an issue by updating its State field."""
        _assert_ok_status(
            self._request(
                f"api/issues/{issue}",
                method="POST",
                headers={"Content-Type": "application/json"},
                data=json.dumps({
                    "customFields": [
                        {
                            "name": "State",
                            "$type": "StateIssueCustomField",
                            "value": {"name": state}
                        }
                    ]
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

    issue_create_parser = subparsers.add_parser("issue-create")
    issue_create_parser.set_defaults(func=YouTrack.issue_create)
    issue_create_parser.add_argument("--project", required=True)
    issue_create_parser.add_argument("--summary", required=True)
    issue_create_parser.add_argument("--description", default="")
    issue_create_parser.add_argument("--type", dest="issue_type", default="")
    issue_create_parser.add_argument("--tags", default="")
    issue_create_parser.add_argument("--assignee", default="")
    issue_create_parser.add_argument("--deduplicate", action="store_true")

    issue_watch_parser = subparsers.add_parser("issue-watch")
    issue_watch_parser.set_defaults(func=YouTrack.issue_watch)
    issue_watch_parser.add_argument("--issue", required=True)
    issue_watch_parser.add_argument("--logins", required=True)

    issue_link_parser = subparsers.add_parser("issue-link")
    issue_link_parser.set_defaults(func=YouTrack.issue_link)
    issue_link_parser.add_argument("--issue", required=True)
    issue_link_parser.add_argument("--type", dest="link_type", required=True,
                                   choices=_LINK_TYPE_MAP.keys())
    issue_link_parser.add_argument("--links", required=True)

    issue_close_parser = subparsers.add_parser("issue-close")
    issue_close_parser.set_defaults(func=lambda yt, issue, resolution:
                                    yt.close_issue(issue, _RESOLUTION_MAP[resolution]))
    issue_close_parser.add_argument("--issue", required=True)
    issue_close_parser.add_argument("--resolution", required=True,
                                    choices=_RESOLUTION_MAP.keys())

    close_issue_parser = subparsers.add_parser("close-issue")
    close_issue_parser.set_defaults(func=YouTrack.close_issue)
    close_issue_parser.add_argument("--issue", required=True)
    close_issue_parser.add_argument("--state", default="Closed (Done)")

    args = parser.parse_args().__dict__

    youtrack = YouTrack(
        base_url=args.pop("base_url"),
        token=args.pop("token"),
    )
    func = args.pop("func")
    result = func(youtrack, **args)
    if result is not None:
        print(json.dumps(result, indent=2))
