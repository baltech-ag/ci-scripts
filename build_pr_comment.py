#!python3
# -*- coding: utf-8 -*-

import io
import os
import json

from common import parse_issues


PR_AUTHOR_NAME = 'CI_PR_AUTHOR_NAME'
PR_TITLE = 'CI_PR_TITLE'
PR_URL = 'CI_PR_URL'
BRANCH_NAME = 'CI_BRANCH_NAME'
BASE_BRANCH_NAME = 'CI_BASE_BRANCH_NAME'
PROJECT_NAME = 'CI_PROJECT_NAME'
PROJECT_URL = 'CI_PROJECT_URL'


def convert_to_comment(author_name, pr_title, pr_url, branch_name,
                       base_branch_name, project_name, project_url):
    comment = io.StringIO()
    comment.write(
        f'<div style="background:#e3fcef;padding:8px;border-radius:4px">\n'
        f'\U0001F535 <b>{author_name}</b> opened a <a href="{pr_url}"><b>pull request</b></a> '
        f'in <a href="{project_url}">{project_name}</a> '
        f'for branch <b>{base_branch_name}</b> \u2190 <b>{branch_name}</b>:\n'
        f'<blockquote>{pr_title}</blockquote>\n'
        f'</div>\n'
    )
    return comment.getvalue()


def create_comment():
    env = os.environ
    issues = parse_issues(env[BRANCH_NAME])
    if len(issues) == 0:
        return {}
    issue = issues[0]
    comment = convert_to_comment(
        env[PR_AUTHOR_NAME],
        env[PR_TITLE],
        env[PR_URL],
        env[BRANCH_NAME],
        env[BASE_BRANCH_NAME],
        env[PROJECT_NAME],
        env[PROJECT_URL])
    return {issue: comment}


def main():
    print(json.dumps(create_comment()))


if __name__ == '__main__':
    main()
