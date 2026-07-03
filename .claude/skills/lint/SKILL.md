---
name: lint
description: |
  Run linters for backend and frontend. Use this skill when the user wants to check code quality, run a linter, or find style/formatting errors. Trigger phrases: "run the linter", "check the code", "lint", "ruff", "eslint", "formatting", "code style".
---

# Lint Skill

## Scope

- "backend" / "python" / "ruff" → Backend only
- "frontend" / "vue" / "eslint" → Frontend only
- no qualifier → both

## Backend (Ruff)

Find the nearest `pyproject.toml` upward from the changed files — that's the run root.

```bash
uv run ruff check .
uv run ruff check . --fix
uv run ruff format .   # only if formatting is explicitly requested
```

## Frontend (ESLint)

Find `package.json` with `eslint` in its dependencies (`find . -name package.json -not -path '*/node_modules/*'`) — run from that directory. If no such file exists, there's no frontend in the repo yet — say so instead of running.

```bash
npm run lint
npm run lint:fix
npm run format   # only if formatting is explicitly requested
```

## Behavior

- **No errors** → `✓ Backend: OK` / `✓ Frontend: OK`
- **Errors found** → show the list of files, ask: autofix or details?
- **After autofix** → show the list of changed files

## Restrictions

- Don't run `ruff format` / `npm run format` unless explicitly requested
- Don't fix code manually if autofix can do it
- `E`, `F` are critical — don't ignore them
