# Pull Request

## Summary

Describe the change and why it is needed. Link related issues with `Closes #NNN`.

## Type of change

- [ ] feat
- [ ] fix
- [ ] docs
- [ ] test
- [ ] refactor
- [ ] chore / ci

## Tests

List verification performed:

- [ ] `cd backend && pytest tests/ -v`
- [ ] `cd backend && python -m compileall -q app tests`
- [ ] `cd frontend && npx tsc -b`
- [ ] `cd frontend && npm run build`
- [ ] Manual verification (describe steps and results):

## Checklist

- [ ] Follows Conventional Commits
- [ ] Branch is up to date with `main`
- [ ] Updated docs (`README.md` / `CHANGELOG.md`) if user-facing
- [ ] No secrets or local-only config committed
- [ ] CI passes (backend + frontend)
