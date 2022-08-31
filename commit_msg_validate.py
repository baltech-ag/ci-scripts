#!python3

import os

from common import retrieve_commits, parse_subject


START_COMMIT = 'CI_COMMIT_BEFORE_SHA'
CUR_COMMIT = 'CI_COMMIT_SHA'
BRANCH_NAME = 'CI_COMMIT_REF_NAME'
PROJECT_DIR = 'CI_PROJECT_DIR'


def validate_commit_msgs():
    env = os.environ
    commits = retrieve_commits(
        env[PROJECT_DIR],
        env[START_COMMIT] if env[BRANCH_NAME] == 'master' else 'origin/master',
        env[CUR_COMMIT])
    for subject in map(parse_subject, commits):
        if not subject.is_valid:
            raise ValueError(f'Invalid Subject: {subject.text!r}')


def main():
    validate_commit_msgs()


if __name__ == '__main__':
    main()
