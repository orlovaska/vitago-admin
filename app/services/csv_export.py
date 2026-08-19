from __future__ import annotations

from pathlib import Path


def export_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    lines = [_join(headers), *(_join(row) for row in rows)]
    content = "\ufeff" + "\n".join(lines)
    path.write_text(content, encoding="utf-8")


def _join(values: list[str]) -> str:
    return ",".join(_escape(value) for value in values)


def _escape(value: str | int | None) -> str:
    if value is None:
        return ""
    text = str(value)
    if any(char in text for char in ",\"\n"):
        return f"\"{text.replace('\"', '\"\"')}\""
    return text
