---
name: llm-wiki
description: |
  Build and maintain an LLM wiki — a personal knowledge base of linked markdown pages.
  Use when the user wants to: build a wiki from sources, add a new source to the wiki,
  find something in the wiki, or check the wiki's state. Pattern from Andrej Karpathy's article.
  Trigger phrases: "add to the wiki", "update the wiki", "find in the wiki", "check the wiki",
  "llm wiki", "ingest", "create a page", "wiki lint".
---

# LLM Wiki Skill

Three layers: **Sources** (immutable) → **Wiki** (LLM-maintained) → **Schema** (structure rules).
Three operations: **Ingest** → **Query** → **Lint**.

## Structure

```
wiki/
├── SCHEMA.md       # structure rules (don't change without an explicit command)
├── INDEX.md        # index of all pages
├── entities/       # people, tools, systems
├── concepts/       # patterns, ideas, terms
├── sources/        # source summaries
└── queries/        # saved answers
```

**File name = slug**: kebab-case, Latin script (transliterate non-Latin), singular.
Examples: "Transformer" → `transformer.md`, "Andrej Karpathy" → `andrej-karpathy.md`, "GPT-4" → `gpt-4.md`.

The slug is the page's only identifier. Always check by slug before creating a page
(`find`/`grep -il` by file name), not by title text — casing and inflection can break
text search on a title.

Every page: frontmatter `tags`, `updated` + markdown. Link to a page with `[[slug]]`
(no `.md`, no path) — since the slug is the file name, this makes the link unambiguously resolvable.

---

## Initialization (if `wiki/` doesn't exist)

Create the directories and an empty `wiki/INDEX.md`. Create `wiki/SCHEMA.md`:

```markdown
# Schema

**Topic:** <from the context of the first source>
**Language:** en

## File names
slug: kebab-case, Latin script (transliterate non-Latin), singular.
Example: "Transformer" → `transformer.md`

## Links
`[[slug]]` — no `.md` and no path, slug = file name without extension

## Tags
Free-form list. Before adding a new tag, grep existing ones in wiki/ and reuse.
```

---

## Ingest (add a source)

1. Read `wiki/SCHEMA.md` and `wiki/INDEX.md`
2. Get the source: URL → WebFetch, file → Read
3. Check for a duplicate source by URL:
   ```bash
   grep -rl "url: <URL>" wiki/sources/
   ```
   If found → update the existing source instead of creating a new one.
4. For each entity/concept:
   - Determine the slug per the convention in `SCHEMA.md`
   - Check if it exists: `find wiki/ -iname "SLUG.md"`
   - Exists → update: add facts, add the source under `## Sources`, update `updated`
   - Doesn't exist → create `wiki/{entities|concepts}/SLUG.md`:
   ```markdown
   ---
   tags: [tag1, tag2]
   updated: YYYY-MM-DD
   ---
   # Title
   Brief definition.
   ## Key facts
   - ...
   ## Links
   - [[other-slug]] — why they're related
   ## Sources
   - [Source title](../sources/url-slug.md)
   ```
5. Create/update `wiki/sources/URL-SLUG.md`:
   ```markdown
   ---
   tags: [source]
   updated: YYYY-MM-DD
   url: https://...
   ---
   # Title
   **Type:** article / paper / book  **Author:** ...  **Date:** ...
   ## Key ideas
   1. ...
   ## Entities mentioned
   [[slug1]], [[slug2]]
   ```
6. Update `INDEX.md`: `- [Title](path.md) — one line`
7. Report: `Created: N (entities: X, concepts: Y) | Updated: M`

---

## Query (find an answer)

0. First check the cache of ready answers: `grep -ril "keyword" wiki/queries/`
1. If not found, search the wiki:
   ```bash
   grep -ril "KEYWORD" wiki/ --include="*.md"
   grep -rn "TERM" wiki/ --include="*.md" -C 2
   ```

Read only the pages found. Answer with links to the files.
If the question is non-trivial, save it under `wiki/queries/` with `tags: [query]`.

---

## Lint (check the wiki)

```bash
# Orphaned pages (not in INDEX)
find wiki/ -name "*.md" ! -name "INDEX.md" ! -name "SCHEMA.md" | while read f; do
  grep -q "$(basename "$f")" wiki/INDEX.md || echo "ORPHAN: $f"
done

# Broken links ([[slug]] with no matching file)
grep -rohE '\[\[[^]]+\]\]' wiki/ | tr -d '[]' | sort -u | while read slug; do
  find wiki/ -iname "${slug}.md" | grep -q . || echo "BROKEN: [[$slug]]"
done

# Stale pages (sorted by date, oldest first)
for f in $(find wiki/ -name "*.md" ! -name "INDEX.md" ! -name "SCHEMA.md"); do
  d=$(grep -m1 "^updated:" "$f" | sed 's/updated: *//')
  echo "$d $f"
done | sort | head -20
```

Report: `Total: N | 🔴 Orphaned: X | 🟡 Broken links: Y | 🔵 Stale >30d: Z`

---

## Restrictions

- Don't modify sources under `sources/`
- Don't read the whole wiki — grep first, then read specific files
- Don't create duplicates — always check by slug before creating
- Don't change `SCHEMA.md` without an explicit request
