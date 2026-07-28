# Set issues to In Review when a PR is opened

## Context

Today a PR body line `closes: <ISSUE>` only has an effect when the PR is merged:
the `closing-issues` job in `.github/workflows/release-actions.yml` parses the PR
body and sets the issue State to `Closed (Done)`.

The issue should already be moved to `In Review` while the review is pending:

- PR opened and **not** a draft -> set issue to `In Review`
- PR opened **as draft** -> do nothing, wait until the draft flag is removed
  (GitHub event `pull_request` / action `ready_for_review`)

## YouTrack State values

The State bundle used by all baltech projects:
`Open`, `In Progress`, `On Hold`, `In Review`, `Closed (Done)`,
`Closed (Won't Do)`, `Closed (Duplicate)`, `Closed (No Action Required)`,
`Closed (Cannot Reproduce)`

So the review state is exactly `In Review`.

## Changes

### 1. `youtrack.py` - generic `set-state` command

`close_issue()` already writes the State field, but its name only fits closing.
Extract the actual field update into `set_state(issue, state)` and let
`close_issue()` delegate to it (CLI subcommands `close-issue` / `issue-close`
stay unchanged).

Add CLI subcommand `set-state` with required `--issue` and `--state`.

### 2. `.github/workflows/release-actions.yml` - new job `review-issues`

Mirrors the existing `closing-issues` job, but runs on PR open / ready-for-review
and sets `In Review` instead of closing:

```yaml
if: >-
  github.event_name == 'pull_request' &&
  (github.event.action == 'ready_for_review' ||
   (github.event.action == 'opened' && github.event.pull_request.draft == false))
```

`closing-issues` stays untouched (its job name may be referenced by required
status checks).

### 3. `templates/org-release-actions.yml` - additional trigger types

The `pull_request` trigger currently only listens to `closed`. Add `opened` and
`ready_for_review` so the new job is triggered at all, and bump the
`# Version:` header (the template hash check warns repos with an outdated copy).

## Notes / non-goals

- `converted_to_draft` does **not** move the issue back - a PR that goes back to
  draft keeps the `In Review` state.
- `reopened` is not handled either.
- The extra trigger types also start the `release-context` job on every opened
  PR. For a non-release branch this ends up in the `commit-pushed` fallback of
  `print_release_context()`, which is harmless; all release jobs stay skipped
  (`branch-created` / `pr-merged` conditions).

## Files

- **Modify:** `youtrack.py`
- **Modify:** `.github/workflows/release-actions.yml`
- **Modify:** `templates/org-release-actions.yml`
