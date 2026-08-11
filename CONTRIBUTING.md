# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## GitHub is used for everything

GitHub is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Create your branch from `main` (see [Branching model](#branching-model)).
2. Run `script/setup/bootstrap` to install dependencies and pre-commit hooks.
3. If you've changed something, update the documentation.
4. Make sure your code passes all checks (using `script/check` for linting and type checking).
5. Test your contribution.
6. Open a pull request against `main`.

## Branching model

`main` is the only long-lived branch and is always release-ready.

| Branch      | Purpose                                                                                                                                                                            | Protected |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| `main`      | release-ready; [release-please](https://github.com/googleapis/release-please) opens a release PR from Conventional Commits, and merging it tags `vX.Y.Z` + cuts the GitHub release | yes       |
| `feature/*` | short-lived work on a single topic; deleted after merge                                                                                                                            | –         |

Keep **Settings → General → "Automatically delete head branches"** enabled — it
cleans up merged `feature/*` branches. The protected `main` branch is never
deleted by this setting.

> **Why no `dev` branch?** An earlier version of this workflow staged changes
> on a separate `dev` branch before promoting them to `main`. In practice this
> added no real safety - CI gates every PR the same way regardless of target
> branch, and local testing works identically on a feature branch - while
> costing recurring manual upkeep: release-please's release commit only ever
> lands on `main`, so `dev` silently drifted out of date after every release
> and had to be manually re-synced before the next promotion. Dropping the
> extra branch removes that drift at the source.

### Workflow

```text
feature/xyz ──PR──▶ main ──release-please──▶ Release (vX.Y.Z)
```

1. **Branch** from `main`: `git switch main && git pull && git switch -c feature/xyz`.
2. **Test locally** before opening the PR: `./script/develop` against your branch,
   `script/check`, `script/test`.
3. **Open a PR against `main`.** CI (`Ruff`, `Hassfest validation`, `HACS validation`,
   `pytest`) must be green; enable "Auto-merge". **Use "Squash and merge"** with a
   [Conventional Commit](https://www.conventionalcommits.org/)-formatted PR title
   (e.g. `feat(mos): add pools, disks, and services entities`) — release-please
   scans commit _subjects_ on `main`'s history for these prefixes, so intermediate
   WIP commits on the feature branch don't need to be conventional themselves,
   but the single squashed commit that lands on `main` does.
4. **Releases are automatic.** On push to `main`, release-please maintains a
   "release PR"; merging that PR pushes the `vX.Y.Z` tag and publishes the GitHub
   release with generated notes. There is no manual tag step and no VERSION file —
   the version is derived from the Conventional Commit history. While the project
   is pre-1.0 (the current `manifest.json` version is `0.x`), the config
   (`bump-minor-pre-major` + `bump-patch-for-minor-pre-major`) keeps every bump
   small: `fix:` and `feat:` → patch (`0.1.0` → `0.1.1`), and a breaking change
   (`!` / `BREAKING CHANGE`) → minor (`0.1.0` → `0.2.0`). From `1.0.0` onward the
   usual SemVer applies: `fix:` → patch, `feat:` → minor, breaking → major.
   Note: release-please opens its release PR using the default `GITHUB_TOKEN`,
   which GitHub's loop protection prevents from triggering downstream
   `pull_request` workflows - so the required status checks never run on it,
   and it currently needs a manual merge (via the GitHub UI, with owner
   privileges) instead of going through auto-merge like a normal PR.
5. **HACS** installs from the default branch (`main`) or a release tag. If you
   want feedback on unreleased work before cutting a real release, push a
   pre-release tag directly (`git tag vX.Y.Z-beta.N <sha> && git push origin
vX.Y.Z-beta.N`, then `gh release create vX.Y.Z-beta.N --prerelease
--target main`) and ask testers to enable "show beta versions" in HACS.
   This is independent of release-please - it only manages the one open
   release PR for the next stable version and ignores unrelated tags.

The `Lint` and `Validate` workflows run on `push` and `pull_request` for
`main`, so every PR is gated the same way.

### Setting up branch protection (one-time)

GitHub → **Settings → Rules → Rulesets → New branch ruleset** (the newer Rulesets
system, not "classic").

1. **Ruleset name:** `protected-branches`
2. **Enforcement status:** `Active`
3. **Bypass list:** leave empty (a bypass would undermine the protection for
   yourself; in an emergency, temporarily set the ruleset to `Disabled`).
4. **Target branches → Add target:** `Include default branch` (= `main`).
5. **Branch rules** (check boxes):
   - ✅ **Restrict deletions**
   - ✅ **Block force pushes**
   - ✅ **Require a pull request before merging**
     - **Required approvals: `0`** ⚠️ — as a solo maintainer you cannot review
       your own PR; setting ≥1 would block you. The PR requirement and status
       checks still apply at 0, and auto-merge works.
   - ✅ **Require status checks to pass**
     - ✅ **Require branches to be up to date before merging**
     - Add these checks: `Ruff`, `Hassfest validation`, `HACS validation`.
6. **Save changes**, then enable **Settings → General → Pull Requests → "Allow
   auto-merge"**. Click "Enable auto-merge" per PR.

## Keeping in sync with the blueprint

This repository was generated from
[jpawlowski/hacs.integration_blueprint](https://github.com/jpawlowski/hacs.integration_blueprint).
The [`Sync from Blueprint Template`](.github/workflows/template-sync.yml)
workflow runs every Monday at 07:00 UTC and opens a pull request whenever the
blueprint has new commits, so adopting scaffolding improvements is a normal PR
review — nothing has to be merged that we don't want.

**What sync may touch.** Only paths _not_ listed in
[`.templatesyncignore`](.templatesyncignore): `script/`, `.devcontainer/`,
`.github/workflows/`, `.github/instructions/`, `schemas/` and similar generic
scaffolding. Our own work — `custom_components/`, `tests/`, `docs/`,
`README.md`, this file, `AGENTS.md`, `pyproject.toml`, `config/` — is excluded
and never overwritten.

**Deleting a synced file requires an ignore entry.** Sync restores anything that
exists upstream but is missing here, so `git rm` alone does not stick. Add the
path to `.templatesyncignore` in the same commit, with a comment saying why.
That is how the Copilot files and the instruction files for features this
integration doesn't have (service actions, repairs) stay deleted.

**Updating workflow files** needs a repository secret named
`TEMPLATE_SYNC_TARGET_PAT` with `contents: write`, `pull requests: write`,
`workflows: write` and `metadata: read`. Without it the run still syncs
everything else and skips only `.github/workflows/*`.

To inspect or adopt something outside the weekly PR:

```shell
./script/compare-blueprint          # full diff of scaffolding paths vs. blueprint/main
./script/compare-blueprint --stat   # just the changed files
git checkout blueprint/main -- <path>   # take a single file back from the blueprint
```

The helper adds a read-only `blueprint` remote in local git config only.

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using GitHub's [issues](../../issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](../../issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People _love_ thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

This project uses:

- [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
- [Pyright](https://github.com/microsoft/pyright) for type checking

Run `script/check` to lint and type-check your code before submitting, or `script/lint` to auto-format and fix linting issues.

**Local validation:** Run `script/hassfest` to validate your integration against Home Assistant's quality standards using the official validation tools. This checks manifest.json, translations, services.yaml (service action definitions), and integration structure locally before pushing to GitHub.

## Code Quality

The integration follows Home Assistant's [integration quality standards](https://developers.home-assistant.io/docs/core/integration-quality-scale/):
full type hints, docstrings that link the relevant Home Assistant docs, a config
flow with reauth and reconfigure support, the coordinator pattern for data
fetching, and explicit error handling that maps API failures onto entity
availability. Keep new code at that level — `script/check` and `script/test`
enforce the mechanical part of it.

## AI-assisted contributions

AI tools may be used for any part of a contribution — see [AI_POLICY.md](AI_POLICY.md). What matters is that the
pull request says honestly how far the code was reviewed and tested: fill in the **Verification context** block in the
pull request template. AI usage, human review, automated testing and real-world testing are separate facts, and a green
`script/check` is not a claim that anyone understood the change.

## Adding a dependency

Four requirements files, each with one job:

| Add to                                     | For                                                                              |
| ------------------------------------------ | -------------------------------------------------------------------------------- |
| `manifest.json` **and** `requirements.txt` | A runtime dependency end users need — keep both in sync, same version constraint |
| `requirements_dev.txt`                     | A Python development tool (type checker, dev-script helpers)                     |
| `requirements_test.txt`                    | A testing tool (pytest plugins, test utilities)                                  |
| `package.json`                             | A Node.js tool (Markdown formatting and linting)                                 |

Home Assistant core's own `requirements_test.txt` already brings ruff,
pre-commit, codespell, pylint, pytest and its usual plugins — `script/setup/bootstrap`
installs those automatically, so don't duplicate them here. After changing a
requirements file, run `uv lock` (the lockfile is maintained manually to keep
sync PRs quiet).

## Test your code modification

This project comes with a complete development environment in a container, easy to launch
if you use Visual Studio Code. With this container you will have a standalone
Home Assistant instance running and already configured with the included
[`configuration.yaml`](./config/configuration.yaml) file.

You can also run tests using `script/test` to ensure your changes don't break existing functionality.

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
