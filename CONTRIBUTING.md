# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## GitHub is used for everything

GitHub is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Create your branch from `dev` (see [Branching model](#branching-model)).
2. Run `script/setup/bootstrap` to install dependencies and pre-commit hooks.
3. If you've changed something, update the documentation.
4. Make sure your code passes all checks (using `script/check` for linting and type checking).
5. Test your contribution.
6. Open a pull request against `dev`.

## Branching model

`main` is always release-ready; `dev` is the integration/staging channel for
testing changes before they reach a release.

| Branch      | Purpose                                                                                                                                                                            | Protected |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| `main`      | release-ready; [release-please](https://github.com/googleapis/release-please) opens a release PR from Conventional Commits, and merging it tags `vX.Y.Z` + cuts the GitHub release | yes       |
| `dev`       | integration/staging; collects features before they go to `main`                                                                                                                    | yes       |
| `feature/*` | short-lived work on a single topic; deleted after merge                                                                                                                            | –         |

Keep **Settings → General → "Automatically delete head branches"** enabled — it
cleans up merged `feature/*` branches. Protected branches (`dev`, `main`) are
never deleted by this setting.

### Workflow

```text
feature/xyz ──PR──▶ dev ──(staging test)──▶ PR ──▶ main ──release-please──▶ Release (vX.Y.Z)
```

1. **Branch** from `dev`: `git switch dev && git pull && git switch -c feature/xyz`.
2. **Open a PR against `dev`.** CI (`Ruff`, `Hassfest validation`, `HACS validation`)
   must be green; enable "Auto-merge" so GitHub merges the final, green state
   automatically. Use [Conventional Commit](https://www.conventionalcommits.org/)
   messages — release-please derives the next version and changelog from them.
3. Test the merged `dev` state (local `./script/develop`, or a HACS beta install
   from a pre-release tag if you cut one).
4. When `dev` is good: **PR `dev → main`** and merge it. Merging to `main` does
   not publish anything by itself.
5. **Releases are automatic.** On push to `main`, release-please maintains a
   "release PR"; merging that PR pushes the `vX.Y.Z` tag and publishes the GitHub
   release with generated notes. There is no manual tag step and no VERSION file —
   the version is derived from the Conventional Commit history. While the project
   is pre-1.0 (the current `manifest.json` version is `0.x`), the config
   (`bump-minor-pre-major` + `bump-patch-for-minor-pre-major`) keeps every bump
   small: `fix:` and `feat:` → patch (`0.1.0` → `0.1.1`), and a breaking change
   (`!` / `BREAKING CHANGE`) → minor (`0.1.0` → `0.2.0`). From `1.0.0` onward the
   usual SemVer applies: `fix:` → patch, `feat:` → minor, breaking → major.
6. **HACS** installs from the default branch (`main`) or a release tag. For a beta,
   push a pre-release tag (`vX.Y.Z-beta.N`) and enable "show beta versions" in HACS.

The `Lint` and `Validate` workflows run on `push` and `pull_request` for both
`main` and `dev`, so PRs against `dev` are gated the same way as PRs against
`main`.

### Setting up branch protection (one-time)

GitHub → **Settings → Rules → Rulesets → New branch ruleset** (the newer Rulesets
system, not "classic"). A single ruleset covers both `main` **and** `dev`.

1. **Ruleset name:** `protected-branches`
2. **Enforcement status:** `Active`
3. **Bypass list:** leave empty (a bypass would undermine the protection for
   yourself; in an emergency, temporarily set the ruleset to `Disabled`).
4. **Target branches → Add target:** `Include default branch` (= `main`) **and**
   `Include by pattern` → `dev` ("Applies to 2 targets").
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
[jpawlowski/hacs.integration_blueprint](https://github.com/jpawlowski/hacs.integration_blueprint)
via GitHub's **"Use this template"**. That records the template on GitHub but
starts a **fresh git history with no common ancestor** — so there is no `git
merge` or "Sync fork" path to pull in later blueprint improvements. Adoption is
manual and deliberate, which is what you want for a project whose integration
code (`custom_components/mos/`) has diverged from the template.

Use the helper to see what changed in the generic scaffolding:

```shell
./script/compare-blueprint          # full diff of scaffolding paths vs. blueprint/main
./script/compare-blueprint --stat   # just the changed files
./script/compare-blueprint --paths  # list the tracked scaffolding paths
```

It adds a read-only `blueprint` remote (local git config only), fetches it, and
diffs a curated set of scaffolding paths (`script/`, `.github/workflows/`,
`.github/instructions/`, `.pre-commit-config.yaml`, `.devcontainer/`,
`pyproject.toml`, `hacs.json`). It deliberately **excludes**
`custom_components/` and `translations/` — that is our own code.

To adopt an upstream change:

```shell
git checkout blueprint/main -- <path>   # take a whole file you have not customized
git cherry-pick <sha>                   # apply a single blueprint commit (resolve conflicts if any)
```

Do this on a branch off `dev`, then open a PR against `dev` like any other
change. Tip: **Watch → Custom → Releases** on the blueprint repo to get notified,
then run the helper every few months — scaffolding improvements are rarely
time-critical.

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

This blueprint follows Home Assistant's [integration quality standards](https://developers.home-assistant.io/docs/core/integration-quality-scale/) as best practices. The code includes:

- ✅ Comprehensive docstrings with links to official documentation
- ✅ Full type hints for better IDE support
- ✅ Config flow with reauthentication support
- ✅ Proper error handling and entity unavailability
- ✅ Coordinator pattern for efficient data fetching

**Don't worry!** You don't need to maintain all of this. The blueprint gives you a solid, well-documented starting point. Feel free to simplify or adapt anything to your needs - the goal is to help you get started quickly with good patterns, not to overwhelm you with requirements.

## Test your code modification

This project comes with a complete development environment in a container, easy to launch
if you use Visual Studio Code. With this container you will have a standalone
Home Assistant instance running and already configured with the included
[`configuration.yaml`](./config/configuration.yaml) file.

You can also run tests using `script/test` to ensure your changes don't break existing functionality.

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
