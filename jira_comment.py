#!python3
# -*- coding: utf-8 -*-

from base64 import b64encode
import json
import os
from subprocess import check_call
import sys
from urllib import request
from urllib.error import HTTPError


_JIRA_COMMENT_FILE = os.environ.get('JIRA_COMMENT_FILE', '')
_JIRA_URL = os.environ.get('JIRA_URL', '')
_JIRA_USER = os.environ.get('JIRA_USER', '')
_JIRA_PASSWORD = os.environ.get('JIRA_PASSWORD', '')


def post_comment(issue: str, comment: str) -> None:
    login = f"{_JIRA_USER}:{_JIRA_PASSWORD}"
    request.urlopen(request.Request(
        f'{_JIRA_URL}/rest/api/2/issue/{issue}/comment',
        headers={
            'Authorization': 'Basic ' + b64encode(login.encode()).decode(),
            'Content-Type': 'application/json',
        },
        data=f'{{"body": "{comment}"}}'.encode(),
    ))


def upload_attachment(issue, attachment):
    check_call([
        'curl',
        '--user', f'{_JIRA_USER}:{_JIRA_PASSWORD}',
        '--request', 'POST',
        '--header', 'X-Atlassian-Token: nocheck',  # disable XSRF check
        '--form', f'file=@{os.path.abspath(attachment)}',
        f'{_JIRA_URL}/rest/api/2/issue/{issue}/attachments',
    ])


def post_comments(comments: dict) -> None:
    for issue, comment in comments.items():
        if isinstance(comment, dict):
            attachments = comment.get('attachments', [])
            comment = comment.get('comment', '')
        else:
            attachments = []
        escaped_comment = comment \
            .replace('\\', '\\\\') \
            .replace('"', '\\"') \
            .replace('\r\n', '\n') \
            .replace('\n', '\\n')
        try:
            for attachment in attachments:
                print(f'Upload attachment {attachment} to Jira Issue {issue}')
                upload_attachment(issue, attachment)
            print(f'Create comment in Jira Issue {issue}')
            post_comment(issue, escaped_comment)
        except HTTPError as e:
            message = f'HTTP Error {e.code} while requesting {e.url}'
            if e.reason:
                message += f', reason: {e.reason}'
            sys.exit(message)


if __name__ == '__main__':
    with open(_JIRA_COMMENT_FILE, mode='r') as cf:
        post_comments(json.load(cf))
