---
name: docs-audit
description: |
  Audit and sync documentation with code. Use this skill when the user wants to check whether docs are up to date, update docs to match code, find stale documentation, remove clutter, or rewrite "plans" as facts. Trigger phrases: "check the docs", "update the docs", "sync docs with code", "docs audit", "check docs".
---

# Docs Audit Skill

Cycle: **Discovery → Triage → Verify → Fix**. All paths and patterns are derived from the project automatically — nothing hardcoded.

---

## Phase 0: Discovery (always first)

```bash
# 1. Find the documentation entry point
find . -name "INDEX.md" -not -path "*/node_modules/*" -not -path "*/.git/*"

# 2. Detect languages by file extensions in git
git ls-files | grep -v "node_modules\|\.git\|dist\|__pycache__" \
  | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -15

# 3. Detect the framework (extension is the language, not the framework — needs a separate signal)
grep -rlE "^\s*(from flask|import flask)" --include="*.py" . 2>/dev/null | head -1
grep -rlE "^\s*(from django|import django)" --include="*.py" . 2>/dev/null | head -1
grep -rlE "^\s*(from fastapi|import fastapi)" --include="*.py" . 2>/dev/null | head -1
grep -l '"express"\|"vue"\|"react"' package.json 2>/dev/null

# 4. Extract source directories mentioned in INDEX.md
# (read INDEX.md once — it's the only file read in full at the start)
```

If `find` in step 1 finds multiple `INDEX.md` files (monorepo), audit each separately,
with its own `DOCS_ROOT`/`SOURCE_DIRS`/`STACK` — don't mix them in one session.

From Discovery, build the session config:
- `DOCS_ROOT` — directory containing INDEX.md
- `SOURCE_DIRS` — source folders (from links in INDEX.md, e.g. `../backend/`, `../frontend/src/`)
- `STACK` — language + framework (Python/Flask, JS/Vue, Go, etc.)

---

## Phase 1: Triage — what changed

```bash
git log --since="30 days ago" --name-only --pretty=format:"" | sort -u | grep -v "^$"
```

Empty (no commits in 30 days) doesn't mean "all fine" — it means the window is uninformative.
Fall back to the last 20 commits instead, and note in the report that the fallback fired:

```bash
git log -20 --name-only --pretty=format:"" | sort -u | grep -v "^$"
```

From the result, extract which `SOURCE_DIRS` are affected → Verify only those.

---

## Phase 2: Verify — structural diff (no file reading)

### 2.1 Broken links in documentation

Resolve each link relative to the doc file's own directory (not `$DOCS_ROOT`) —
links can point to sibling docs (`.md`) too, not just sources:

```bash
find "$DOCS_ROOT" -name "*.md" | while read doc; do
  dir=$(dirname "$doc")
  grep -oE '\]\([^)]+\.(py|js|vue|ts|go|rb|rs|md)\)' "$doc" | sed 's/^](//; s/)$//' \
    | while read link; do [ -f "$dir/$link" ] || echo "BROKEN: $doc -> $link"; done
done
```

### 2.2 Orphan files: in the code, not in the docs

For each affected `SOURCE_DIR` from Triage (recursively — sources can live in nested folders):

```bash
# Get the list of real files
find "$SOURCE_DIR" -type f -not -path "*/__pycache__/*" -not -path "*/node_modules/*" \
  | sed "s|^$SOURCE_DIR/||" | sort

# Get the list of files mentioned in the corresponding doc file
grep -oh '[a-zA-Z0-9_-]*\.\(py\|js\|vue\|ts\)' "$DOCS_ROOT/X.md" | sort -u
```

Diff the two lists (by basename) — add entries for files missing from the docs.

### 2.3 Counters (framework-specific, pick by STACK)

**Flask/FastAPI** (Python):
```bash
for f in "$ROUTES_DIR"/*.py; do
  echo "$(basename $f): $(grep -c '\.route(' $f 2>/dev/null || echo 0)"
done
```

**Express** (JS/TS):
```bash
for f in "$ROUTES_DIR"/*.js; do
  echo "$(basename $f): $(grep -cE 'router\.(get|post|put|delete|patch)\(' $f 2>/dev/null || echo 0)"
done
```

**Django**:
```bash
grep -c 'path\|re_path' "$ROUTES_DIR"/urls.py 2>/dev/null
```

Compare with the numbers in the docs. Fix discrepancies.

### 2.4 Orphan docs: in docs/, not in INDEX.md

```bash
# Find all .md files under docs
find "$DOCS_ROOT" -name "*.md" -not -name "INDEX.md" | sort

# Check whether each is mentioned in INDEX.md
grep -oh '[a-zA-Z0-9_/.-]*\.md' "$DOCS_ROOT/INDEX.md" | sort -u
```

Diff → add links in INDEX.md for orphan files.

### 2.5 Planning language

```bash
grep -rn "planned\|will be implemented\|will be added\|TODO\|FIXME\|coming soon\|WIP" \
  "$DOCS_ROOT" --include="*.md" \
  | grep -v "plans/\|roadmap\|ROADMAP"
```

---

## Phase 3: Fix

1. **Broken links** → fix the path or remove the line
2. **Orphan files** → add a minimal entry (file name, purpose in one phrase)
3. **Wrong counters** → fix the number in the doc
4. **Orphan docs** → add a link in INDEX.md
5. **Planning language** → rewrite as fact if implemented, otherwise move to ROADMAP

---

## Restrictions

- Don't read source files — grep/ls only
- Read a doc file only when a discrepancy is found
- Don't document private functions (`_` prefix)
- Don't touch files under `plans/` — that's a decision archive

---

## Report

```
Stack: <detected>  |  Docs root: <path>  |  Source dirs: <list>
Checked: N files | Changed: N | Broken links: N | Orphan files: N | Counters: N fixed
- docs/backend.md — processing.py: 3→5 endpoints
- docs/frontend.md — added: Foo.vue, useBar.js
```
