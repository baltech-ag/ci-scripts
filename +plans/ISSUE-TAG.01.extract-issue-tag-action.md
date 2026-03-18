# Plan: Extract `issue-tag` Action

## Context
Tagging is currently embedded in `issue_create()` (lines 211-213 of `youtrack.py`). Extracting it into a standalone `issue-tag` action allows tagging existing issues independently of creation.

## Changes

### 1. `youtrack.py` — Add `issue_tag()` method (after `get_tag_ids`, ~line 233)
```python
def issue_tag(self, issue: str, tags: str) -> None:
    """Add tags to an issue (comma-separated tag names)."""
    tag_ids = self.get_tag_ids()
    for tag in tags.split(","):
        tag = tag.strip()
        if not tag:
            continue
        _assert_ok_status(self._request(
            f"api/issues/{issue}/tags",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"id": tag_ids[tag]}).encode()
        ))
```
Follows the `issue_watch` pattern: iterate comma-separated values, POST each individually.

### 2. `youtrack.py` — Add CLI subcommand (~line 395, after issue-search)
```python
issue_tag_parser = subparsers.add_parser("issue-tag")
issue_tag_parser.set_defaults(func=YouTrack.issue_tag)
issue_tag_parser.add_argument("--issue", required=True)
issue_tag_parser.add_argument("--tags", required=True)
```

### 3. `youtrack.py` — Update `issue_create()` to delegate to `issue_tag()`
Replace inline tag handling with delegation to `issue_tag()` after issue creation.

### 4. `actions/issue-tag/action.yaml` — New action file
Follow `issue-watch` pattern with inputs: `issue`, `tags`, `token`, `url`.

### 5. `actions/issue-create/action.yaml` — Keep `tags` input (no change needed)
The `--tags` CLI arg is still passed through; `issue_create()` handles delegation internally.

## Files
- `youtrack.py` — add method + CLI subcommand + refactor `issue_create`
- `actions/issue-tag/action.yaml` — new file

## Verification
- `python youtrack.py --help` shows `issue-tag` subcommand
- `python youtrack.py issue-tag --help` shows `--issue` and `--tags` args
- Existing `issue-create` with `--tags` still works (delegates internally)
