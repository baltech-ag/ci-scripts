#!python3
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "qrcode[pil]",
# ]
# ///

import os
import json

import qrcode

from common import retrieve_commits, group_by_issue


AUTHOR_NAME = 'CI_AUTHOR_NAME'
REPO_URL = 'CI_REPO_URL'
CUR_COMMIT = 'CI_COMMIT_SHA'
NUM_COMMITS = 'CI_NUM_COMMITS'
BRANCH_NAME = 'CI_COMMIT_REF_NAME'
PROJECT_NAME = 'CI_PROJECT_NAME'
PROJECT_DIR = 'CI_PROJECT_DIR'
TICKET_ID = 'CI_TICKET_ID'
ANDROID_URL = 'CI_ANDROID_URL'
ANDROID_QRCODE = 'CI_ANDROID_QRCODE'


def convert_to_comment(author_name, project_name, repo_url, branch_name,
                       android_url, android_qrcode):
    return (f'\U0001F6A9 <b>{author_name}</b> prepared an '
            f'<a href="{android_url}"><b>Android</b> test build</a> '
            f'for <a href="{repo_url}"><b>{project_name}</b></a> '
            f'on branch <b>{branch_name}</b>:<br><br>\n'
            f'![]({android_qrcode})')


def create_comments():
    env = os.environ
    if env[TICKET_ID]:
        affected_issues = [env[TICKET_ID]]
    else:
        all_commits = retrieve_commits(
            env[PROJECT_DIR],
            'HEAD~' + env[NUM_COMMITS],
            env[CUR_COMMIT])
        affected_issues = group_by_issue(all_commits).keys()
    comment = convert_to_comment(
        env[AUTHOR_NAME],
        env[PROJECT_NAME],
        env[REPO_URL],
        env[BRANCH_NAME],
        env[ANDROID_URL],
        env[ANDROID_QRCODE],
    )

    qrcode.make(env[ANDROID_URL]).save(env[ANDROID_QRCODE])
    
    return {
        issue: {
            "comment": comment,
            "attachments": [env[ANDROID_QRCODE]],
        } for issue in affected_issues
    }


def main():
    print(json.dumps(create_comments()))


if __name__ == '__main__':
    main()
