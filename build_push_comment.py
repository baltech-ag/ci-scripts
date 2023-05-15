#!python3

import os
import io
import json
from collections import defaultdict

from common import retrieve_commits, parse_subject, parse_issues


JIRA_URL = 'JIRA_URL'
JIRA_USER = 'JIRA_USER'
JIRA_PASSWORD = 'JIRA_PASSWORD'
REPO_URL = 'CI_REPO_URL'
START_COMMIT = 'CI_COMMIT_BEFORE_SHA'
CUR_COMMIT = 'CI_COMMIT_SHA'
BRANCH_NAME = 'CI_COMMIT_REF_NAME'
PROJECT_NAME = 'CI_PROJECT_NAME'
PROJECT_DIR = 'CI_PROJECT_DIR'


def group_by_issue(commits):
    affected_issues = defaultdict(list)
    for commit in commits:
        commit_msg = f'{commit.subject}\n{commit.body}'
        for issue in parse_issues(commit_msg):
            affected_issues[issue].append(commit)
    return dict(affected_issues)


def convert_to_comment(commits, repo_url, branch_name, project_name):
    comment = io.StringIO()
    bgcolor = '#deebff' if branch_name == 'master' else '#ffffce'
    comment.write(f'{{panel:bgColor={bgcolor}|borderStyle=none}}\n')
    authors = set()
    for commit in commits:
        subject = parse_subject(commit)
        comment.write(
            f"{subject.symbol} "
            f"[{subject.text}|{repo_url}/commit/{commit.commitid}]\n")
        authors.add(commit.author)
    comment.write('\n')
    comment.write(
        f'{{color:#4c9aff}}{" ".join(authors)} contributed to '
        f'[{project_name}|{repo_url}/tree/{branch_name}]')
    if branch_name != 'master':
        comment.write(f' at *{branch_name}*')
    comment.write('{color}\n')
    comment.write('{panel}')
    return comment.getvalue()


def create_jira_comments():
    env = os.environ
    new_branch = all(c == '0' for c in env[START_COMMIT])
    all_commits = retrieve_commits(
        env[PROJECT_DIR],
        'origin/master' if new_branch else env[START_COMMIT],
        env[CUR_COMMIT])
    affected_issues = group_by_issue(all_commits)
    return {
        issue: convert_to_comment(
            reversed(commits),
            env[REPO_URL],
            env[BRANCH_NAME],
            env[PROJECT_NAME]
        )
        for issue, commits in affected_issues.items()
    }


def main():
    print(json.dumps(create_jira_comments()))


if __name__ == '__main__':
    main()
