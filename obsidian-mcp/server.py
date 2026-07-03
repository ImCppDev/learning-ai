import os
from pathlib import Path

from fastmcp import FastMCP

VAULT_PATH_ENV = "OBSIDIAN_VAULT_PATH"

_raw_vault_path = os.environ.get(VAULT_PATH_ENV)
if not _raw_vault_path:
    raise RuntimeError(f"Переменная окружения {VAULT_PATH_ENV} не задана")

VAULT_ROOT = Path(_raw_vault_path).resolve()
if not VAULT_ROOT.is_dir():
    raise RuntimeError(f"{VAULT_PATH_ENV}={VAULT_ROOT} не существует или не является директорией")

mcp = FastMCP(name="Obsidian")


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


@mcp.tool
def list_notes(folder: str = "") -> list[str]:
    base = _resolve(folder) if folder else VAULT_ROOT
    return sorted(
        p.relative_to(VAULT_ROOT).as_posix()
        for p in base.rglob("*.md")
        if p.is_file()
    )


@mcp.tool
def search_notes(query: str, limit: int = 20) -> list[dict]:
    query_lower = query.lower()
    results = []

    for md_path in sorted(VAULT_ROOT.rglob("*.md")):
        if len(results) >= limit:
            break
        if not md_path.is_file():
            continue

        rel_path = md_path.relative_to(VAULT_ROOT).as_posix()

        if query_lower in md_path.name.lower():
            results.append({"path": rel_path, "line": 0, "snippet": md_path.name})
            if len(results) >= limit:
                break

        for line_no, line in enumerate(md_path.read_text(encoding="utf-8").splitlines(), start=1):
            if query_lower in line.lower():
                results.append({"path": rel_path, "line": line_no, "snippet": line})
                if len(results) >= limit:
                    break

    return results


@mcp.tool
def read_note(path: str) -> str:
    return _read_note(path)


@mcp.resource("note://{path}")
def get_note(path: str) -> str:
    return _read_note(path)


if __name__ == "__main__":
    mcp.run()
