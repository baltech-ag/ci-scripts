#!python3

import os
import sys

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
            print()
            print("-"*60)
            print(f"UNGUELTIGE COMMIT MESSAGE: {subject.text}")
            print("-"*60)
            print()
            msg = subject.text.upper()
            if env[BRANCH_NAME] == 'master' or \
                    not (msg.startswith("DRAFT:") or msg.startswith("WIP:")):
                sys.exit(-1)


def main():
    validate_commit_msgs()


if __name__ == '__main__':
    main()
