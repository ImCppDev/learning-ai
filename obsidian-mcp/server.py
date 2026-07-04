import fnmatch
import os
import re
from pathlib import Path

from fastmcp import FastMCP

VAULT_PATH_ENV = "OBSIDIAN_VAULT_PATH"
SNIPPET_MAX_LEN = 300

_raw_vault_path = os.environ.get(VAULT_PATH_ENV)
if not _raw_vault_path:
    raise RuntimeError(f"Переменная окружения {VAULT_PATH_ENV} не задана")

VAULT_ROOT = Path(_raw_vault_path).resolve()
if not VAULT_ROOT.is_dir():
    raise RuntimeError(f"{VAULT_PATH_ENV}={VAULT_ROOT} не существует или не является директорией")

mcp = FastMCP(name="Obsidian")

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
# A trailing space after '#' marks a heading, not a tag, so tags never match here.
# The leading lookbehind keeps '#' from matching mid-word or right after a path
# separator, e.g. inside a URL fragment like example.com/#section.
TAG_RE = re.compile(r"(?<![\w#/])#([\w\-/]+)")
CODE_SPAN_RE = re.compile(r"`[^`]*`")
LINK_DEST_RE = re.compile(r"\]\([^)]*\)")
URL_RE = re.compile(r"https?://\S+")
LIST_ITEM_RE = re.compile(r'"[^"]*"|\'[^\']*\'|[^,]+')


def _resolve(rel_path: str) -> Path:
    candidate = (VAULT_ROOT / rel_path).resolve()
    if not candidate.is_relative_to(VAULT_ROOT):
        raise ValueError(f"Путь {rel_path!r} выходит за пределы vault")
    return candidate


def _read_note(path: str) -> str:
    abs_path = _resolve(path)
    if not abs_path.is_file():
        raise FileNotFoundError(f"Заметка {path!r} не найдена")
    return abs_path.read_text(encoding="utf-8")


def _iter_md_files(base: Path = VAULT_ROOT) -> list[Path]:
    return sorted(p for p in base.rglob("*.md") if p.is_file())


def _truncate(text: str, max_len: int = SNIPPET_MAX_LEN) -> str:
    if len(text) > max_len:
        return text[:max_len] + "…"
    return text


def _split_frontmatter(content: str) -> tuple[str, str]:
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return "", content
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return "", content
    return "".join(lines[1:end_idx]), "".join(lines[end_idx + 1:])


def _parse_frontmatter_text(fm_text: str) -> dict:
    result: dict = {}
    current_key = None
    for line in fm_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- ") and current_key is not None:
            result[current_key].append(stripped[2:].strip().strip("\"'"))
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                items = LIST_ITEM_RE.findall(value[1:-1])
                result[key] = [item.strip().strip("\"'") for item in items if item.strip()]
                current_key = None
            elif value:
                result[key] = value.strip("\"'")
                current_key = None
            else:
                result[key] = []
                current_key = key
    return result


def _note_tags(content: str) -> set[str]:
    fm_text, body = _split_frontmatter(content)
    fm = _parse_frontmatter_text(fm_text) if fm_text else {}
    fm_tags = fm.get("tags", [])
    if isinstance(fm_tags, str):
        fm_tags = [fm_tags]
    tags = {t.strip().lstrip("#") for t in fm_tags if t and t.strip()}
    clean_body = CODE_SPAN_RE.sub("", body)
    clean_body = LINK_DEST_RE.sub("]", clean_body)
    clean_body = URL_RE.sub("", clean_body)
    tags.update(TAG_RE.findall(clean_body))
    return tags


def _wikilink_regex(stem: str) -> re.Pattern:
    return re.compile(r"\[\[(?:[^\[\]]*/)?" + re.escape(stem) + r"(?=\]\]|\||#)")


def _rewrite_wikilinks(old_stem: str, new_stem: str, exclude_path: Path) -> None:
    pattern = _wikilink_regex(old_stem)
    replacement = "[[" + new_stem
    for md_path in _iter_md_files():
        if md_path == exclude_path:
            continue
        content = md_path.read_text(encoding="utf-8")
        new_content = pattern.sub(lambda _: replacement, content)
        if new_content != content:
            md_path.write_text(new_content, encoding="utf-8")


@mcp.tool
def list_notes(folder: str = "", pattern: str = "", tag: str = "") -> list[str]:
    """List note paths under a folder, optionally filtered by glob pattern and/or tag."""
    base = _resolve(folder) if folder else VAULT_ROOT
    results = []
    for md_path in _iter_md_files(base):
        rel_path = md_path.relative_to(VAULT_ROOT).as_posix()
        if pattern and not fnmatch.fnmatch(rel_path, pattern):
            continue
        if tag and tag not in _note_tags(md_path.read_text(encoding="utf-8")):
            continue
        results.append(rel_path)
    return results


@mcp.tool
def search_notes(query: str, limit: int = 20, max_per_file: int = 3) -> list[dict]:
    """Search notes by filename or line content, case-insensitive.

    Filenames are checked first across the whole vault, then content lines
    (capped at `max_per_file` per note) until `limit` results are reached.
    """
    query_lower = query.lower()
    results = []
    md_files = _iter_md_files()

    for md_path in md_files:
        if len(results) >= limit:
            break
        if query_lower in md_path.name.lower():
            rel_path = md_path.relative_to(VAULT_ROOT).as_posix()
            results.append({"path": rel_path, "line": 0, "snippet": _truncate(md_path.name)})

    for md_path in md_files:
        if len(results) >= limit:
            break
        rel_path = md_path.relative_to(VAULT_ROOT).as_posix()
        per_file_count = 0
        for line_no, line in enumerate(md_path.read_text(encoding="utf-8").splitlines(), start=1):
            if per_file_count >= max_per_file or len(results) >= limit:
                break
            if query_lower in line.lower():
                results.append({"path": rel_path, "line": line_no, "snippet": _truncate(line)})
                per_file_count += 1

    return results


@mcp.tool
def read_note(path: str, heading: str = "", offset: int = 0, limit: int = 0) -> str:
    """Read a note, optionally scoped to a heading's section or a line range.

    `heading` returns that section (up to the next heading of equal-or-shallower
    level). Otherwise, if `limit` > 0, returns lines [offset, offset + limit).
    With neither, returns the full content.
    """
    content = _read_note(path)

    if heading:
        lines = content.splitlines(keepends=True)
        target = heading.strip().lower()
        start_idx = None
        start_level = None
        for i, line in enumerate(lines):
            match = HEADING_RE.match(line.rstrip("\n"))
            if not match:
                continue
            level = len(match.group(1))
            if start_idx is None:
                if match.group(2).strip().lower() == target:
                    start_idx = i
                    start_level = level
                continue
            if level <= start_level:
                return "".join(lines[start_idx:i])
        if start_idx is None:
            raise ValueError(f"Заголовок {heading!r} не найден в заметке {path!r}")
        return "".join(lines[start_idx:])

    if limit > 0:
        lines = content.splitlines(keepends=True)
        start = max(offset - 1, 0)
        return "".join(lines[start:start + limit])

    return content


@mcp.tool
def create_note(path: str, content: str = "") -> str:
    """Create a new note at the given vault-relative path, failing if it already exists."""
    abs_path = _resolve(path)
    if abs_path.exists():
        raise FileExistsError(f"Заметка {path!r} уже существует")
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
    return abs_path.relative_to(VAULT_ROOT).as_posix()


@mcp.tool
def edit_note(path: str, content: str) -> str:
    """Overwrite an existing note's full content."""
    abs_path = _resolve(path)
    if not abs_path.is_file():
        raise FileNotFoundError(f"Заметка {path!r} не найдена")
    abs_path.write_text(content, encoding="utf-8")
    return abs_path.relative_to(VAULT_ROOT).as_posix()


@mcp.tool
def patch_note(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """Replace `old_string` with `new_string` in a note without overwriting the rest."""
    abs_path = _resolve(path)
    if not abs_path.is_file():
        raise FileNotFoundError(f"Заметка {path!r} не найдена")
    if not old_string:
        raise ValueError("old_string не может быть пустой строкой")
    content = abs_path.read_text(encoding="utf-8")
    count = content.count(old_string)
    if count == 0:
        raise ValueError(f"Строка {old_string!r} не найдена в заметке {path!r}")
    if count > 1 and not replace_all:
        raise ValueError(
            f"Строка {old_string!r} встречается в заметке {path!r} {count} раз(а); "
            "добавьте больше контекста вокруг строки или передайте replace_all=True"
        )
    new_content = content.replace(old_string, new_string, -1 if replace_all else 1)
    abs_path.write_text(new_content, encoding="utf-8")
    return abs_path.relative_to(VAULT_ROOT).as_posix()


@mcp.tool
def delete_note(path: str) -> str:
    """Delete a note by its vault-relative path."""
    abs_path = _resolve(path)
    if not abs_path.is_file():
        raise FileNotFoundError(f"Заметка {path!r} не найдена")
    abs_path.unlink()
    return abs_path.relative_to(VAULT_ROOT).as_posix()


@mcp.tool
def move_note(path: str, new_path: str) -> str:
    """Move (or rename) a note, rewriting `[[wikilinks]]` to it elsewhere in the vault."""
    src_abs = _resolve(path)
    if not src_abs.is_file():
        raise FileNotFoundError(f"Заметка {path!r} не найдена")
    dst_abs = _resolve(new_path)
    if dst_abs.exists():
        raise FileExistsError(f"Заметка {new_path!r} уже существует")
    old_stem = src_abs.stem
    new_stem = dst_abs.stem
    dst_abs.parent.mkdir(parents=True, exist_ok=True)
    src_abs.rename(dst_abs)
    if old_stem != new_stem:
        _rewrite_wikilinks(old_stem, new_stem, exclude_path=dst_abs)
    return dst_abs.relative_to(VAULT_ROOT).as_posix()


@mcp.tool
def rename_note(path: str, new_name: str) -> str:
    """Rename a note in place, keeping it in the same folder."""
    new_path = (Path(path).parent / new_name).as_posix()
    return move_note(path, new_path)


@mcp.tool
def get_frontmatter(path: str) -> dict:
    """Parse and return a note's YAML-ish frontmatter block as a dict."""
    content = _read_note(path)
    fm_text, _ = _split_frontmatter(content)
    if not fm_text:
        return {}
    return _parse_frontmatter_text(fm_text)


@mcp.tool
def list_tags() -> dict[str, list[str]]:
    """Map every tag found in the vault (frontmatter + inline #tags) to the notes containing it."""
    mapping: dict[str, set[str]] = {}
    for md_path in _iter_md_files():
        rel_path = md_path.relative_to(VAULT_ROOT).as_posix()
        for tag in _note_tags(md_path.read_text(encoding="utf-8")):
            mapping.setdefault(tag, set()).add(rel_path)
    return {tag: sorted(paths) for tag, paths in sorted(mapping.items())}


@mcp.tool
def get_backlinks(path: str, limit: int = 50) -> list[dict]:
    """Find every `[[wikilink]]` reference to a note anywhere in the vault."""
    abs_path = _resolve(path)
    if not abs_path.is_file():
        raise FileNotFoundError(f"Заметка {path!r} не найдена")
    pattern = _wikilink_regex(abs_path.stem)
    results = []
    for md_path in _iter_md_files():
        if len(results) >= limit:
            break
        rel_path = md_path.relative_to(VAULT_ROOT).as_posix()
        for line_no, line in enumerate(md_path.read_text(encoding="utf-8").splitlines(), start=1):
            if len(results) >= limit:
                break
            if pattern.search(line):
                results.append({"path": rel_path, "line": line_no, "snippet": _truncate(line)})
    return results


@mcp.resource("note://{path}")
def get_note(path: str) -> str:
    return _read_note(path)


if __name__ == "__main__":
    mcp.run()
