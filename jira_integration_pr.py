#!python3
# -*- coding: utf-8 -*-

import io
import os

from common import jira_append_comment, parse_issues


JIRA_URL = 'JIRA_URL'
JIRA_USER = 'JIRA_USER'
JIRA_PASSWORD = 'JIRA_PASSWORD'
PR_AUTHOR_NAME = 'CI_PR_AUTHOR_NAME'
PR_TITLE = 'CI_PR_TITLE'
PR_URL = 'CI_PR_URL'
BRANCH_NAME = 'CI_BRANCH_NAME'
BASE_BRANCH_NAME = 'CI_BASE_BRANCH_NAME'
PROJECT_NAME = 'CI_PROJECT_NAME'
PROJECT_URL = 'CI_PROJECT_URL'


def convert_to_comment(author_name, pr_title, pr_url, branch_name,
                       base_branch_name, project_name, project_url):
    bgcolor = '#deebff' if branch_name == 'master' else '#ffffce'
    comment = io.StringIO()
    comment.write(
        f'{{panel:bgColor={bgcolor}|borderStyle=none}}\n'
        f"*{author_name}* opened a *pull request* "
        f"in [{project_name}|{project_url}] "
        f"for branch *{base_branch_name}* ← *{branch_name}*:"
        "{quote}"
        f"[{pr_title}|{pr_url}]"
        "{quote}\n"
        "{panel}"
    )
    return comment.getvalue()


def create_jira_comment():
    env = os.environ
    issues = parse_issues(env[BRANCH_NAME])
    if len(issues) == 0:
        return
    issue = issues[0]
    comment = convert_to_comment(
        env[PR_AUTHOR_NAME],
        env[PR_TITLE],
        env[PR_URL],
        env[BRANCH_NAME],
        env[BASE_BRANCH_NAME],
        env[PROJECT_NAME],
        env[PROJECT_URL])
    jira_append_comment(
        issue,
        comment,
        env[JIRA_URL],
        env[JIRA_USER],
        env[JIRA_PASSWORD])


def main():
    create_jira_comment()


if __name__ == '__main__':
    main()
