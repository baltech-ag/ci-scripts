#!python3

import os
import io
import json

from common import retrieve_commits, parse_subject, group_by_issue


REPO_URL = 'CI_REPO_URL'
START_COMMIT = 'CI_COMMIT_BEFORE_SHA'
CUR_COMMIT = 'CI_COMMIT_SHA'
BRANCH_NAME = 'CI_COMMIT_REF_NAME'
PROJECT_NAME = 'CI_PROJECT_NAME'
PROJECT_DIR = 'CI_PROJECT_DIR'


def convert_to_comment(commits, repo_url, branch_name, project_name):
    comment = io.StringIO()
    bgcolor = '#deebff' if branch_name == 'master' else '#ffffce'
    comment.write(f'<div style="background:{bgcolor};padding:8px;border-radius:4px">\n')
    authors = set()
    for commit in commits:
        subject = parse_subject(commit)
        comment.write(
            f'{subject.symbol} '
            f'<a href="{repo_url}/commit/{commit.commitid}">{subject.text}</a><br>\n')
        authors.add(commit.author)
    comment.write('<br>\n')
    comment.write(
        f'<span style="color:#4c9aff">{" ".join(authors)} contributed to '
        f'<a href="{repo_url}/tree/{branch_name}">{project_name}</a>')
    if branch_name != 'master':
        comment.write(f' at <b>{branch_name}</b>')
    comment.write('</span>\n')
    comment.write('</div>')
    return comment.getvalue()


def create_comments():
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
    print(json.dumps(create_comments()))


if __name__ == '__main__':
    main()
