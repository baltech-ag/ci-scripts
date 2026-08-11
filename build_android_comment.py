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
import sys
from string import Template

import qrcode

from common import retrieve_commits, group_by_issue
from youtrack import YouTrack


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
RELEASE_VERSION = 'CI_RELEASE_VERSION'
PROJECT = 'CI_PROJECT'
VERSION_TEMPLATE = 'CI_VERSION_TEMPLATE'
YOUTRACK_URL = 'CI_YOUTRACK_URL'
YOUTRACK_TOKEN = 'CI_YOUTRACK_TOKEN'


def convert_to_comment(author_name, project_name, repo_url, branch_name,
                       android_url, android_qrcode):
    return (f'\U0001F6A9 <b>{author_name}</b> prepared an '
            f'<a href="{android_url}"><b>Android</b> test build</a> '
            f'for <a href="{repo_url}"><b>{project_name}</b></a> '
            f'on branch <b>{branch_name}</b>:<br><br>\n'
            f'![]({android_qrcode})')


def convert_to_release_comment(release_version, android_qrcode):
    return (f'Android Produktiv-Build Version {release_version}\n'
            f'\n'
            f'![]({android_qrcode}){{width=184px}}')


def find_release_issues(env):
    fix_version = Template(env[VERSION_TEMPLATE]).safe_substitute(
        version=env[RELEASE_VERSION])
    query = (f'project: {{{env[PROJECT]}}} '
             f'tag: {{Public Release}} '
             f'Fix versions: {{{fix_version}}}')
    issues = YouTrack(env[YOUTRACK_URL], env[YOUTRACK_TOKEN]).issue_search(query)
    if not issues:
        _warn(f'no release ticket found for query `{query}`')
    elif len(issues) > 1:
        _warn(f'multiple release tickets found for query `{query}`: '
              + ', '.join(issues))
    return issues


def _warn(msg):
    prefix = '::warning::' if os.environ.get('CI') else 'WARNING: '
    print(f'{prefix}{msg}', file=sys.stderr)


def create_comments():
    env = os.environ
    if env.get(RELEASE_VERSION):
        affected_issues = find_release_issues(env)
        comment = convert_to_release_comment(
            env[RELEASE_VERSION],
            env[ANDROID_QRCODE],
        )
    else:
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
