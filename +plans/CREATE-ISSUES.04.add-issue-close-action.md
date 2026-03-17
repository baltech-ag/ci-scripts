# Plan: Add issue-close Action

## Context

Wrap the existing `close_issue` method with a resolution enum for cleaner usage.

## Resolution Mapping (from YouTrack SDK project)

| CLI value              | YouTrack State                 |
|------------------------|--------------------------------|
| `done`                 | Closed (Done)                  |
| `wont-do`              | Closed (Won't Do)              |
| `duplicate`            | Closed (Duplicate)             |
| `no-action-required`   | Closed (No Action Required)    |
| `cannot-reproduce`     | Closed (Cannot Reproduce)      |

## Changes

### 1. `youtrack.py` — Constant + new CLI subcommand `issue-close`

Add `_RESOLUTION_MAP` dict mapping CLI enum → YouTrack state string. Reuse existing `close_issue(issue, state)` method — no new class method needed, just a new CLI subcommand that translates the enum before calling `close_issue`.

### 2. `actions/issue-close/action.yaml` — New composite action

Inputs: `issue`, `resolution` (enum), `token`, `url`

## Files

- **Modify:** `youtrack.py` (add constant + CLI subcommand)
- **Create:** `actions/issue-close/action.yaml`
