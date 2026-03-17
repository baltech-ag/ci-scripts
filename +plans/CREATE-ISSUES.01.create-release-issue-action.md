# Plan: Create Release Issue Action

## Context

The SDK release process needs a YouTrack ticket to track the public release. Currently no `create-issue` functionality exists in ci-scripts. The action should create the ticket and output the issue ID so the finalize job can close it later.

## Decisions

- **Summary**: Caller passes pre-built summary string. Action stays generic.
- **Deduplication**: `--deduplicate` flag searches for existing issue with same summary in the project. If found, returns existing issue ID instead of creating a new one.
- **Scope**: Issue creation + deduplication only. Linking and watchers are out of scope for now.

## Changes

### 1. `youtrack.py` — New API Methods

Add to the `YouTrack` class:

- **`get_user_by_email(email)`** — GET `/api/users?query={email}&fields=id,login,email&$top=1`
- **`search_issues(project, summary)`** — GET `/api/issues?query=...&fields=idReadable&$top=1` — for deduplication
- **`create_issue(project, summary, description, type, tag, assignee_email)`** — POST `/api/issues?fields=idReadable`
  - Sets project via `{"shortName": "..."}`, summary, description
  - Sets Type custom field (`SingleEnumIssueCustomField`)
  - Sets Assignee custom field via resolved user ID
  - Adds tag via `tags` array
  - Returns `idReadable` (e.g. `SDK-123`)

### 2. `youtrack.py` — New CLI Subcommand `issue-create`

```
issue-create --project SDK --summary "..." --description "..." \
  --type Task --tag "Public Release" \
  --assignee-email user@example.com \
  --deduplicate
```

Flow:
1. If `--deduplicate`: search for existing issue with same summary → return existing ID if found
2. Resolve assignee user ID by email
3. Create issue → get `idReadable`
4. Print JSON `{"idReadable": "SDK-123"}`

### 3. `actions/issue-create/action.yaml` — New Composite Action

Inputs: `project`, `summary`, `description`, `type`, `tag`, `assignee-email`, `deduplicate`, `token`, `url`

Output: `issue-id` — the created (or found) issue's readable ID

## Files to Modify/Create

- **Modify:** `youtrack.py`
- **Create:** `actions/issue-create/action.yaml`

## Verification

1. Run `issue-create` CLI against YouTrack, verify issue with correct fields
2. Run again with `--deduplicate` — should return same issue ID
3. Test existing `close-issue` against the created issue
