#!python3
# -*- coding: utf-8 -*-

import os
import json

from common import retrieve_commits, group_by_issue


AUTHOR_NAME = 'CI_AUTHOR_NAME'
REPO_URL = 'CI_REPO_URL'
CUR_COMMIT = 'CI_COMMIT_SHA'
NUM_COMMITS = 'CI_NUM_COMMITS'
BRANCH_NAME = 'CI_COMMIT_REF_NAME'
PROJECT_NAME = 'CI_PROJECT_NAME'
PROJECT_DIR = 'CI_PROJECT_DIR'
ANDROID_URL = 'CI_ANDROID_URL'
ANDROID_QRCODE = 'CI_ANDROID_QRCODE'


def convert_to_comment(author_name, project_name, repo_url, branch_name,
                       android_url, android_qrcode):
    return (f"(*b) *{author_name}* prepared an"
            f"[*Android* test build|{android_url}] "
            f"for [*{project_name}*|{repo_url}] "
            f"on branch *{branch_name}*:\n\n"
            f"!{android_qrcode}|width=250!")


def create_jira_comments():
    env = os.environ
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
    return {
        issue: {
            "comment": comment,
            "attachments": [env[ANDROID_QRCODE]],
        } for issue in affected_issues
    }


def main():
    print(json.dumps(create_jira_comments()))


if __name__ == '__main__':
    main()
