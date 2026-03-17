# Plan: Add issue-link Action

## Context

After creating a release issue, we need to link referenced SDK/FW tickets to it. The token does not have Commands API permissions, so we use the Issues REST API.

## Link Types (from YouTrack instance)

Discovered via `linkedIssueCounts` on live issues:

| CLI value           | YT internal name | Direction | Seen on            |
|---------------------|------------------|-----------|--------------------|
| `depends-on`        | Depend           | OUTWARD   | TS-897, FW-806     |
| `is-required-for`   | Depend           | INWARD    | FW-777, SDK-194    |
| `relates-to`        | Relate           | BOTH      | FW-777, DOC-361    |
| `parent-for`        | Subtask          | INWARD    | DOC-361            |
| `subtask-of`        | Subtask          | OUTWARD   | (inverse of above) |

IDs are instance-specific → single GET `/api/issueLinkTypes?fields=id,name` at runtime, build `{name: id}` map once.

## Changes

### 1. `youtrack.py` — Constants + methods + CLI subcommand

```python
_LINK_TYPE_MAP = {
    "depends-on":       ("Depend",  "OUTWARD"),
    "is-required-for":  ("Depend",  "INWARD"),
    "relates-to":       ("Relate",  "BOTH"),
    "parent-for":       ("Subtask", "INWARD"),
    "subtask-of":       ("Subtask", "OUTWARD"),
}
```

- **`get_link_type_ids()`** — GET `/api/issueLinkTypes?fields=id,name` → `{name: id}` dict
- **`issue_link(issue, link_type, links)`**
  - Look up `(yt_name, direction)` from `_LINK_TYPE_MAP`
  - Get ID via `get_link_type_ids()[yt_name]`
  - For each target: POST `/api/issues/{issue}/links` with `{"direction": "...", "linkType": {"id": "..."}, "issues": [{"idReadable": "TARGET"}]}`
- CLI: `issue-link --issue SDK-123 --type depends-on --links "SDK-1,FW-2"`
  - `--type` uses `choices=_LINK_TYPE_MAP.keys()`

### 2. `actions/issue-link/action.yaml` — New composite action

Inputs: `issue`, `type` (enum string), `links` (comma-separated), `token`, `url`

## Files

- **Modify:** `youtrack.py`
- **Create:** `actions/issue-link/action.yaml`
