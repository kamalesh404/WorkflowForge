# Contributing to WorkflowForge

Thank you for your interest in contributing to WorkflowForge. This document describes how to set up your environment, follow our commit conventions, run checks, and submit pull requests.

## Code of Conduct

By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

1. Fork the repository on GitHub.
2. Clone your fork locally:

   ```bash
   git clone https://github.com/<your-username>/workflowforge.git
   cd workflowforge
   ```

3. Add the upstream remote:

   ```bash
   git remote add upstream https://github.com/kamalesh404/workflowforge.git
   git fetch upstream
   ```

4. Set up the backend:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install pytest httpx
   ```

5. Set up the frontend:

   ```bash
   cd frontend
   npm ci
   ```

## Branching

- Create a feature branch from `main` (or `master` if that is the default in your clone):

  ```bash
  git checkout -b feat/short-description
  ```

- Use short, descriptive branch names with a prefix:
  - `feat/` for new features
  - `fix/` for bug fixes
  - `docs/` for documentation only
  - `chore/` for tooling, CI, or refactoring
  - `test/` for test-only changes

- Keep branches focused on a single change. Rebase on upstream before opening a PR:

  ```bash
  git fetch upstream
  git rebase upstream/main
  ```

## Conventional Commits

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>
```

Allowed types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `ci`, `build`.

Examples:

```
feat(engine): add per-task timeout support
fix(api): return 404 for missing execution logs
docs(readme): update quick start instructions
test(engine): cover cycle detection edge case
```

Rules:

- Use lowercase type and imperative mood ("add", not "added").
- Keep the subject line under 72 characters.
- Include a body for non-trivial changes explaining the why.
- Reference issues with `Closes #123` in the body when applicable.

## Checks

Run these checks before pushing. CI will run the same steps.

Backend (Python 3.12):

```bash
cd backend
python -m py_compile $(git ls-files '*.py')
pytest tests/ -v
```

Frontend (Node 20):

```bash
cd frontend
npm ci
npx tsc -b
npm run build
```

A PR must have passing backend and frontend CI jobs.

## Pull Request Process

1. Ensure your branch is up to date with upstream `main`.
2. Run backend (`pytest`) and frontend (`tsc -b`, `vite build`) checks locally.
3. Push to your fork and open a pull request against `main` using the provided PR template.
4. Fill in summary, type of change, tests performed, and checklist.
5. Link related issues.
6. One maintainer review is required. Address feedback with new commits; do not force-push after review has started unless asked.
7. Squash-merge is preferred. Keep the final commit message in Conventional Commits format.

## Reporting Issues

Use the bug report or feature request templates in `.github/ISSUE_TEMPLATE/`. Include reproduction steps, expected behavior, logs, and environment details.

## License

Contributions are licensed under the MIT License. See [LICENSE](LICENSE).
