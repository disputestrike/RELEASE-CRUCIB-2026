# Branch protection (fifty-point #10)

Merges to `main` should require the **`verify-all-passed`** job from workflow **Verify full stack** (`.github/workflows/ci-verify-full.yml`).

## Option A — script (fastest if you have repo admin)

1. Install [GitHub CLI](https://cli.github.com/) and run `gh auth login` (token must allow **administration** on the repo).
2. From the repo root:

```powershell
.\scripts\enable_branch_protection.ps1
```

On Linux/macOS:

```bash
chmod +x scripts/enable_branch_protection.sh
./scripts/enable_branch_protection.sh main "Verify full stack / verify-all-passed"
```

If GitHub returns an error about the context name, list what your last commit actually reports:

```bash
gh api repos/OWNER/REPO/commits/HEAD/check-runs -q ".check_runs[].name"
```

Pass that exact string as `-Context` / second argument.

## Option B — GitHub UI

Repo **Settings** → **Branches** → add/edit rule for `main` → **Require status checks** → enable **Require status checks to pass before merging** → select **Verify full stack / verify-all-passed** (or the name shown in the list).

## What I cannot do from the codebase

GitHub does not allow branch protection to be turned on by committing a file. Someone with **admin** on the repository must run the script or use the UI once.
