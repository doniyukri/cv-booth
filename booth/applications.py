"""Read the local applications log into a collapsed ledger."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApplicationRecord:
    """One company + position from the applications log."""

    when: str
    date: str
    company: str
    position: str
    pdf: str
    count: int


def parse_application_log_line(line: str) -> dict[str, str] | None:
    """Split a tab-separated applications log line.

    Why:
        `save_application` appends timestamp, company, position, and PDF name.
        The booth ledger needs those fields without failing on blank or old lines.

    Args:
        line: One line from `applications/log.txt`.

    Returns:
        Field map, or None when the line is not a complete log row.
    """
    parts = line.strip().split("\t")
    if len(parts) < 4:
        return None
    when = parts[0].strip()
    company = parts[1].strip()
    position = parts[2].strip()
    pdf = parts[3].strip()
    if not when or not company or not position or not pdf:
        return None
    date = when[:10] if len(when) >= 10 else when
    return {
        "when": when,
        "date": date,
        "company": company,
        "position": position,
        "pdf": pdf,
    }


def list_applications(log_path: Path) -> list[ApplicationRecord]:
    """Newest unique company + position rows, with reprint counts.

    Why:
        Preview reprints of the same vacancy clutter the booth. The ledger keeps
        the latest PDF and shows how many times that pair was printed.

    Args:
        log_path: Path to `applications/log.txt`.

    Returns:
        Records sorted by timestamp, newest first.
    """
    if not log_path.exists():
        return []
    collapsed: dict[tuple[str, str], ApplicationRecord] = {}
    for line in log_path.read_text(encoding="utf-8").splitlines():
        parsed = parse_application_log_line(line)
        if parsed is None:
            continue
        key = (parsed["company"].casefold(), parsed["position"].casefold())
        previous = collapsed.get(key)
        count = previous.count + 1 if previous else 1
        collapsed[key] = ApplicationRecord(
            when=parsed["when"],
            date=parsed["date"],
            company=parsed["company"],
            position=parsed["position"],
            pdf=parsed["pdf"],
            count=count,
        )
    return sorted(collapsed.values(), key=lambda row: row.when, reverse=True)
