# Add Python CI and Automated Releases

## Why

The repository has a substantial standard-library Python test suite but no GitHub Actions
workflow to run it on pull requests or after changes merge. Regressions can therefore reach
`main` without the checks contributors run locally.

Releases are also manual. The canonical version currently lives in `SKILL.md`, while the README
badge and `CHANGELOG.md` must be kept in sync by hand. That duplication makes missed or
inconsistent release metadata likely.

## What Changes

- Add a GitHub Actions CI workflow that runs the existing Python suite
  (`python3 -m unittest discover -s forge/tests`) on pull requests and pushes to `main`.
- Keep CI intentionally Python-only: it does not install Node.js, Playwright, Chromium, or add
  browser coverage.
- Add an automated release workflow that runs after qualifying Conventional Commit changes land
  on `main`.
- Determine semantic versions from commit intent: `fix:` creates a patch release, `feat:` creates
  a minor release, and `!`/`BREAKING CHANGE:` creates a major release. Changes without a
  releasable type do not create a release.
- Treat `SKILL.md` front matter (`version`) as the sole version authority. The workflow updates
  the README version badge and `CHANGELOG.md` from that new version; neither may become an
  independent version source.
- Prepend a dated Keep a Changelog-compatible release section, create a guarded
  `chore(release): vX.Y.Z` commit, tag it `vX.Y.Z`, and create the corresponding GitHub release.
- Configure only the permissions necessary for the release workflow to write its release commit,
  tag, and GitHub release. The generated release commit must not trigger another version bump.

## Capabilities

### New Capabilities

- `python-continuous-integration`: Required, repeatable execution of the existing Python test
  suite for proposed and merged changes.
- `automated-semver-release`: Conventional-Commit-driven release metadata, tags, and GitHub
  releases synchronized from `SKILL.md`.

## Impact

- New files: GitHub Actions workflow definitions under `.github/workflows/` and any small,
  dependency-free release helper required to update project metadata consistently.
- Updated files: `SKILL.md`, `README.md`, and `CHANGELOG.md` only when a release is produced.
- Contributors use Conventional Commit prefixes for release-worthy changes.
- Repository settings may need to permit GitHub Actions to write release commits and tags to
  `main`, including any matching branch-protection allowance.

## Non-Goals

- Adding Chromium, Playwright, Node.js, or visual/browser testing to CI.
- Changing, replacing, or expanding the existing Python test suite.
- Publishing packages to PyPI, npm, or another registry.
- Adding a second version file or moving version authority away from `SKILL.md`.
- Releasing on every merge regardless of commit intent.
