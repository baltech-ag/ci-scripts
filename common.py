import re
import subprocess
from collections import defaultdict, namedtuple


ISSUE_REGEX = re.compile(r'\b[A-Za-z]{2,4}-\d+\b')
ISSUE_REGEX_BLACKLIST = (
    "RS-232",
    "UTF-8",
    "UTF-16",
)
_ISSUE_COMPILED_REGEX_BLACKLIST = [re.compile(f"^{pattern}$") for pattern in ISSUE_REGEX_BLACKLIST]

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


def parse_issues(text):
    unique_issues = set(map(str.upper, ISSUE_REGEX.findall(text)))
    return [t for t in unique_issues if not any(pattern.match(t) for pattern in _ISSUE_COMPILED_REGEX_BLACKLIST)]


def group_by_issue(commits):
    affected_issues = defaultdict(list)
    for commit in commits:
        commit_msg = f'{commit.subject}\n{commit.body}'
        for issue in parse_issues(commit_msg):
            affected_issues[issue].append(commit)
    return dict(affected_issues)


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
