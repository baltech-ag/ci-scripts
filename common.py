import re
import subprocess
from collections import namedtuple


COMMITTYPES = {
    'feature': '(+)',
    'bugfix': '(x)',
    'refactoring': '(*)',
    'internal': '(i)',
    'release': '(flag)',
    'next-version-start': '(flagoff)'}
SUBJECT_REGEX = re.compile(rf'^\[({"|".join(COMMITTYPES)})] (.*)')

Commit = namedtuple('Commit', 'commitid, author, subject, body')
Subject = namedtuple('subject', 'is_valid symbol text')


def retrieve_commits(project_dir, start_commit, cur_commit='HEAD'):
    git_log_output = subprocess.check_output(
        ['git', '-C', project_dir, 'log',
         f'{start_commit}..{cur_commit}',
         '--format=%H%x00%aN%x00%s%x00%b%x01']).decode()
    return [Commit(*log.strip().split('\x00'))
               for log in git_log_output.split('\x01') if log.strip()]


def parse_subject(commit):
    match = SUBJECT_REGEX.match(commit.subject)
    if match:
        is_valid = True
        symbol = COMMITTYPES[match.group(1)]
        text = match.group(2)
    else:
        is_valid = False
        symbol = ''
        text = commit.subject
    return Subject(is_valid, symbol, text)
