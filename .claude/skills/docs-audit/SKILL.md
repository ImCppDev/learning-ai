---
name: docs-audit
description: |
  Аудит и синхронизация документации с кодом. Используй этот скилл когда пользователь хочет проверить актуальность документации, обновить доки под код, найти устаревшую документацию, удалить ненужное, или переписать «планы» как факты. Триггерные фразы: «проверь документацию», «актуализируй доки», «обнови документацию», «синхронизируй доки с кодом», «docs audit», «check docs».
---

# Docs Audit Skill

Цикл: **Discovery → Triage → Verify → Fix**. Все пути и паттерны выводятся автоматически из проекта — хардкода нет.

---

## Фаза 0: Discovery (всегда первая)

```bash
# 1. Найти точку входа в документацию
find . -name "INDEX.md" -not -path "*/node_modules/*" -not -path "*/.git/*"

# 2. Определить языки по расширениям файлов в git
git ls-files | grep -v "node_modules\|\.git\|dist\|__pycache__" \
  | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -15

# 3. Определить фреймворк (расширение — это язык, не фреймворк, нужен отдельный сигнал)
grep -rlE "^\s*(from flask|import flask)" --include="*.py" . 2>/dev/null | head -1
grep -rlE "^\s*(from django|import django)" --include="*.py" . 2>/dev/null | head -1
grep -rlE "^\s*(from fastapi|import fastapi)" --include="*.py" . 2>/dev/null | head -1
grep -l '"express"\|"vue"\|"react"' package.json 2>/dev/null

# 4. Извлечь исходные директории, упомянутые в INDEX.md
# (читай INDEX.md один раз — это единственный файл, который читается полностью на старте)
```

Если `find` в шаге 1 находит несколько `INDEX.md` (монорепо) — веди аудит по каждому отдельно,
со своими `DOCS_ROOT`/`SOURCE_DIRS`/`STACK`, не смешивай в одну сессию.

По результатам Discovery составь конфиг сессии:
- `DOCS_ROOT` — директория с INDEX.md
- `SOURCE_DIRS` — папки с исходниками (из ссылок в INDEX.md, вида `../backend/`, `../frontend/src/`)
- `STACK` — язык + фреймворк (Python/Flask, JS/Vue, Go, etc.)

---

## Фаза 1: Triage — что менялось

```bash
git log --since="30 days ago" --name-only --pretty=format:"" | sort -u | grep -v "^$"
```

Пусто (нет коммитов за 30 дней) → это не «всё ок», а значит окно неинформативно.
Возьми вместо него последние 20 коммитов и отметь в отчёте, что сработал fallback:

```bash
git log -20 --name-only --pretty=format:"" | sort -u | grep -v "^$"
```

Из результата выдели: какие `SOURCE_DIRS` затронуты → только по ним делай Verify.

---

## Фаза 2: Verify — структурный diff (без чтения файлов)

### 2.1 Битые ссылки в документации

Резолвь каждую ссылку относительно директории самого doc-файла (не `$DOCS_ROOT`) —
ссылки бывают и на соседние доки (`.md`), не только на исходники:

```bash
find "$DOCS_ROOT" -name "*.md" | while read doc; do
  dir=$(dirname "$doc")
  grep -oE '\]\([^)]+\.(py|js|vue|ts|go|rb|rs|md)\)' "$doc" | sed 's/^](//; s/)$//' \
    | while read link; do [ -f "$dir/$link" ] || echo "BROKEN: $doc -> $link"; done
done
```

### 2.2 Orphan-файлы: есть в коде, нет в доках

Для каждой затронутой `SOURCE_DIR` из Triage (рекурсивно — исходники бывают во вложенных папках):

```bash
# Получить список реальных файлов
find "$SOURCE_DIR" -type f -not -path "*/__pycache__/*" -not -path "*/node_modules/*" \
  | sed "s|^$SOURCE_DIR/||" | sort

# Получить список упомянутых файлов в соответствующем doc-файле
grep -oh '[a-zA-Z0-9_-]*\.\(py\|js\|vue\|ts\)' "$DOCS_ROOT/X.md" | sort -u
```

Diff этих двух списков (по basename) — добавь строки для файлов, которых нет в доках.

### 2.3 Счётчики (framework-specific, выбирай по STACK)

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

Сравни с числами в документации. Исправь расхождения.

### 2.4 Orphan docs: есть в docs/, нет в INDEX.md

```bash
# Найти все .md в поддиректориях docs
find "$DOCS_ROOT" -name "*.md" -not -name "INDEX.md" | sort

# Проверить, упомянут ли каждый в INDEX.md
grep -oh '[a-zA-Z0-9_/.-]*\.md' "$DOCS_ROOT/INDEX.md" | sort -u
```

Diff → добавь ссылки в INDEX.md для orphan-файлов.

### 2.5 Плановый язык

```bash
grep -rn "планируется\|будет реализован\|будет добавлен\|TODO\|FIXME\|coming soon\|WIP" \
  "$DOCS_ROOT" --include="*.md" \
  | grep -v "plans/\|roadmap\|ROADMAP"
```

---

## Фаза 3: Fix

1. **Битые ссылки** → исправь путь или удали строку
2. **Orphan-файлы** → добавь минимальную строку (имя файла, назначение в 1 фразе)
3. **Неверные счётчики** → исправь число в доке
4. **Orphan docs** → добавь ссылку в INDEX.md
5. **Плановый язык** → перепиши как факт если реализовано, иначе перенеси в ROADMAP

---

## Запреты

- Не читай файлы исходников — только grep/ls
- Читай doc-файл только если обнаружено расхождение
- Не документируй приватные функции (префикс `_`)
- Не трогай файлы в `plans/` — это архив решений

---

## Отчёт

```
Stack: <detected>  |  Docs root: <path>  |  Source dirs: <list>
Проверено: N файлов | Изменено: N | Битых ссылок: N | Orphan-файлов: N | Счётчики: N исправлено
- docs/backend.md — processing.py: 3→5 эндпоинтов
- docs/frontend.md — добавлены: Foo.vue, useBar.js
```
