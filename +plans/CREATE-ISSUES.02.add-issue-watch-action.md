# Plan: Add issue-watch Action

## Context

After creating a release issue via `issue-create`, we need to add watchers. This adds a new `issue-watch` action and CLI subcommand.

## Changes

### 1. `youtrack.py` — New method + CLI subcommand

- **`issue_watch(issue, emails)`** — For each comma-separated email: resolve user via existing `get_user_by_email`, then POST `/api/issues/{issue}/watchers` with `{"id": user_id}`.
- CLI: `issue-watch --issue SDK-123 --emails "user1@example.com,user2@example.com"`

### 2. `actions/issue-watch/action.yaml` — New composite action

Inputs: `issue`, `emails` (comma-separated), `token`, `url`

## Files

- **Modify:** `youtrack.py`
- **Create:** `actions/issue-watch/action.yaml`
