# Central PyPI publish workflow

## Context

Python packages of baltech-ag shall be published to TestPyPI/PyPI via the Release
Actions pipeline. First user is baltech-ag/morphtest (repo side is built in the
parallel workspace `pypi` of the morphtest project), then baltech-ag/bec2format.
Neither PyPI nor TestPyPI has a `morphtest` package yet.

Lint, test and build stay in each repo's `repo-release-actions-deploy.yml`, because
the projects differ (morphtest: `inv lint`/`inv tests` with ty and an OS x Python
matrix; bec2format: `inv lint`/`inv test` with mypy; BaltechSDK builds on a
self-hosted Windows runner with embedded DLLs). ci-scripts centralizes only:

1. the version convention (composite action `actions/pypi-version`)
2. the upload (reusable workflow `release-actions-deploy-pypi.yml`)

Neither may reference `baltech-ag/ci-scripts/...@master` internally: a reusable
workflow cannot reliably know its own ref, so while morphtest tests against
`@pypi-deploy` an internal `@master` reference would run the old code. All logic is
inline in the two files.

## Decisions

- Version source is the `VERSION` file (version-file from release-actions).
  pyproject.toml reads it via `dynamic = ["version"]` +
  `[tool.setuptools.dynamic] version = {file = "VERSION"}` (setuptools or hatch,
  not `uv_build`). This is the repo's responsibility; ci-scripts does **not** verify
  that the built package has the expected version.
- Only normalized PEP 440 versions are allowed. A padded version like `1.05.00`
  fails with `::error::` naming the normalized form (`1.5.0`). bec2format must switch
  to `1.5.0` first (affects its tags `v1.5.x`, version branches `v1.5` and YouTrack
  versions).
- Dev builds (`deploy-mode=development`, every push incl. the `[release]` commit on
  the release-* branch): version is `<version>.dev${{ github.run_number }}`, e.g.
  `0.2.0` -> `0.2.0.dev50` (no patch bump, same scheme as BaltechSDK). Upload only to
  TestPyPI with `skip-existing` (re-runs keep the run_number).
- Releases (`deploy-mode=release`, tag push): version unchanged, upload only to PyPI,
  strict (no `skip-existing`, an existing version fails the job).
- Consequence of no patch bump: dev builds installed with an additional
  `--extra-index-url https://pypi.org/simple/` must be pinned exactly
  (`morphtest==0.2.0.dev50`), otherwise pip prefers the release `0.2.0`.
- Auth via the org secrets `TEST_PYPI_TOKEN` / `PYPI_TOKEN` (visibility `all`) with
  `pypa/gh-action-pypi-publish@release/v1` (`password:`), no Trusted Publishing.
  The tokens must be account-scoped so the first upload can create the project.
- No separate `twine check`: the pypa action verifies metadata by default
  (`verify-metadata: true`).
- One publish call per package. The package is given explicitly, exactly as the
  prefix in the dist filenames (no name normalization).

## 1. `actions/pypi-version/action.yaml` (new)

Composite action, called by the repo's build job before `uv build`.

Inputs:
- `deploy-mode` (required): `development` | `release`
- `version-file` (required): path to the version file

Steps (bash):
1. Read and strip the version file.
2. Fail with `::error::` if it is not a normalized `X.Y.Z` (no leading zeros in any
   component), naming the normalized form.
3. `development`: write `<version>.dev${{ github.run_number }}` into the file.
   `release`: leave the file unchanged. Any other deploy-mode: `::error::`.
4. Output `version` (the version that is now in the file).

Outputs:
- `version`

## 2. `.github/workflows/release-actions-deploy-pypi.yml` (new)

Reusable workflow (`workflow_call`), style like `release-actions-deploy-downloads.yml`.

Inputs:
- `deploy-mode` (required): `development` | `release`
- `artifact-name` (required): artifact with the built dists (uploaded by the repo)
- `package` (required): package name exactly as in the dist filenames

Single job on `ubuntu-24.04`:
1. `actions/download-artifact@v8` into `artifact/`.
2. Select `artifact/<package>-*` (wheels and sdist) into `dist/`; fail with
   `::error::` if nothing matches. Derive the version from the filenames (must be
   one version, otherwise `::error::`).
3. `development`: publish to `https://test.pypi.org/legacy/` with
   `TEST_PYPI_TOKEN`, `skip-existing: true`.
   `release`: publish to PyPI with `PYPI_TOKEN`.
4. Write a link to the package version into the step summary and as
   `::notice::`.

Outputs:
- `package-name`
- `package-version`
- `package-url`: `https://test.pypi.org/project/<name>/<version>/` (development) or
  `https://pypi.org/project/<name>/<version>/` (release)

## 3. Documentation

Usage comment with a call example at the top of both new files. Templates and
README stay unchanged (there is no README; docs live in the Confluence wiki).

## Repo side (reference, done in the morphtest workspace)

```yaml
build:
  needs: [lint, test]
  runs-on: ubuntu-24.04
  outputs:
    version: ${{ steps.version.outputs.version }}
  steps:
    - uses: actions/checkout@v7
    - uses: astral-sh/setup-uv@v8
    - id: version
      uses: baltech-ag/ci-scripts/actions/pypi-version@master
      with:
        deploy-mode: ${{ inputs.deploy-mode }}
        version-file: ${{ inputs.version-file }}
    - run: uv build
    - uses: actions/upload-artifact@v7
      with:
        name: dist
        path: dist/
        retention-days: 5
publish:
  needs: [build]
  uses: baltech-ag/ci-scripts/.github/workflows/release-actions-deploy-pypi.yml@master
  with:
    deploy-mode: ${{ inputs.deploy-mode }}
    artifact-name: dist
    package: morphtest
  secrets: inherit
```

## Test

morphtest references action and workflow with `@pypi-deploy` and does the first real
TestPyPI upload with it. Then the ci-scripts PR is merged, morphtest switches to
`@master`; a PyPI release only after that.
