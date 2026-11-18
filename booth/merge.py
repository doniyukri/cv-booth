"""Merge an AI tailor slice onto the master RenderCV YAML."""

from __future__ import annotations

import copy
import re
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

CONTENT_KEYS = ("headline", "profile", "experience", "skills", "languages")
META_KEYS = ("position", "company")
ALLOWED_KEYS = META_KEYS + CONTENT_KEYS
_ALLOWED = frozenset(ALLOWED_KEYS)
_SECTION_KEYS = frozenset({"profile", "experience", "skills", "languages"})
PAGE_SIZES = {
    "a4": "a4",
    "letter": "us-letter",
    "us-letter": "us-letter",
}


class MergeError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def _yaml() -> YAML:
    yaml = YAML(typ="safe", pure=True)
    yaml.default_flow_style = False
    return yaml


def strip_fences(text: str) -> str:
    """Unwrap a single Markdown YAML block while preserving invalid input."""
    text = text.strip()
    lines = text.splitlines()
    if len(lines) < 2:
        return text
    opening = re.fullmatch(r"(`{3,}|~{3,})(?:yaml|yml)?\s*", lines[0], re.IGNORECASE)
    if opening is None:
        return text
    marker = opening.group(1)
    closing = lines[-1].strip()
    if len(closing) < len(marker) or set(closing) != {marker[0]}:
        return text
    return "\n".join(lines[1:-1]).strip()


def parse_slice(raw: str) -> dict[str, Any]:
    text = strip_fences(raw)
    if not text:
        return {}
    try:
        data = _yaml().load(text)
    except YAMLError as exc:
        problem = getattr(exc, "problem", None) or str(exc)
        raise MergeError([f"Paste is not valid YAML. {problem}"]) from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise MergeError(
            ["Paste must be a YAML mapping of keys, not a list or string."]
        )
    extra = [str(key) for key in data if key not in _ALLOWED]
    if extra:
        extra.sort()
        allowed = ", ".join(ALLOWED_KEYS)
        raise MergeError(
            [
                f"Unknown key{'' if len(extra) == 1 else 's'}: {', '.join(extra)}. "
                f"Allowed: {allowed}."
            ]
        )
    return dict(data)


def merge_slice(master: dict[str, Any], slice_data: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(master)
    cv = merged.setdefault("cv", {})
    sections = cv.setdefault("sections", {})
    if "headline" in slice_data:
        cv["headline"] = slice_data["headline"]
    for key in _SECTION_KEYS:
        if key in slice_data:
            sections[key] = slice_data[key]
    return merged


def application_meta(slice_data: dict[str, Any]) -> tuple[str, str]:
    """Position and company for the PDF name. Not written onto the CV."""
    missing = [key for key in META_KEYS if not str(slice_data.get(key) or "").strip()]
    if missing:
        raise MergeError(
            [
                "YAML must include top-level position and company "
                "(the job you are applying to). They name the PDF and are not printed on the CV."
            ]
        )
    position = str(slice_data["position"]).strip()
    company = str(slice_data["company"]).strip()
    return position, company


def master_slice(master: dict[str, Any]) -> dict[str, Any]:
    cv = master.get("cv", {})
    sections = cv.get("sections", {})
    out: dict[str, Any] = {}
    if "headline" in cv:
        out["headline"] = cv["headline"]
    for key in ("profile", "experience", "skills", "languages"):
        if key in sections:
            out[key] = sections[key]
    return out


def slug_part(value: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", value.strip(), flags=re.UNICODE)
    cleaned = re.sub(r"[\s-]+", "_", cleaned)
    return cleaned.strip("_")


def _as_float(value: Any) -> float | None:
    if value is None or value is False or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    for suffix in ("pt", "in", "cm", "mm", "em"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    try:
        return float(text)
    except ValueError:
        return None


def style_from_master(master: dict[str, Any]) -> dict[str, Any]:
    """Flat numbers the styling panel edits. Units are inches or points."""
    design = master.get("design") or {}
    page = design.get("page") or {}
    typo = design.get("typography") or {}
    size = typo.get("font_size") or {}
    header = design.get("header") or {}
    titles = design.get("section_titles") or {}
    sections = design.get("sections") or {}
    highlights = (design.get("entries") or {}).get("highlights") or {}
    body = _as_float(size.get("body")) or 10

    def em_or_pt(raw: Any, default: float) -> float:
        if raw is None:
            return default
        text = str(raw).strip().lower()
        number = _as_float(text)
        if number is None:
            return default
        if text.endswith("em"):
            return round(number * body, 2)
        if text.endswith("cm"):
            return round(number * 28.3465, 2)
        return round(number, 2)

    return {
        "top": _as_float(page.get("top_margin")) or 0.5,
        "bottom": _as_float(page.get("bottom_margin")) or 0.5,
        "side": _as_float(page.get("left_margin")) or 0.55,
        "body": body,
        "name": _as_float(size.get("name")) or 26,
        "headline": _as_float(size.get("headline")) or 10.5,
        "connections": _as_float(size.get("connections")) or 8,
        "lineSpacing": em_or_pt(typo.get("line_spacing"), 6),
        "sectionAbove": em_or_pt(titles.get("space_above"), 12),
        "sectionBelow": em_or_pt(titles.get("space_below"), 8),
        "betweenJobs": em_or_pt(sections.get("space_between_regular_entries"), 10),
        "betweenSkills": em_or_pt(sections.get("space_between_text_based_entries"), 4),
        "beforeBullets": em_or_pt(highlights.get("space_above"), 4),
        "betweenBullets": em_or_pt(highlights.get("space_between_items"), 2),
        "bulletIndent": em_or_pt(highlights.get("space_between_bullet_and_text"), 6),
        "alignment": typo.get("alignment") or "justified-with-no-hyphenation",
        "headerAlignment": header.get("alignment") or "center",
        "sectionTitle": titles.get("type") or "centered_with_centered_partial_line",
        "sections": [
            str(key) for key in (master.get("cv") or {}).get("sections") or {}
        ],
    }


def apply_design(merged: dict[str, Any], style: Any) -> dict[str, Any]:
    """Override design from the styling panel. Content is untouched."""
    if not isinstance(style, dict) or not style:
        return merged
    design = merged.setdefault("design", {})
    page = design.setdefault("page", {})
    typo = design.setdefault("typography", {})
    font = typo.setdefault("font_size", {})
    header = design.setdefault("header", {})
    titles = design.setdefault("section_titles", {})
    sections = design.setdefault("sections", {})
    entries = design.setdefault("entries", {})
    highlights = entries.setdefault("highlights", {})

    def put(bucket: dict[str, Any], field: str, key: str, unit: str) -> None:
        number = _as_float(style.get(key))
        if number is None:
            return
        bucket[field] = f"{number:g}{unit}"

    put(page, "top_margin", "top", "in")
    put(page, "bottom_margin", "bottom", "in")
    side = _as_float(style.get("side"))
    if side is not None:
        page["left_margin"] = f"{side:g}in"
        page["right_margin"] = f"{side:g}in"
    put(font, "body", "body", "pt")
    put(font, "name", "name", "pt")
    put(font, "headline", "headline", "pt")
    put(font, "connections", "connections", "pt")
    put(typo, "line_spacing", "lineSpacing", "pt")
    put(titles, "space_above", "sectionAbove", "pt")
    put(titles, "space_below", "sectionBelow", "pt")
    put(sections, "space_between_regular_entries", "betweenJobs", "pt")
    put(sections, "space_between_text_based_entries", "betweenSkills", "pt")
    put(highlights, "space_above", "beforeBullets", "pt")
    put(highlights, "space_between_items", "betweenBullets", "pt")
    put(highlights, "space_between_bullet_and_text", "bulletIndent", "pt")
    alignment = style.get("alignment")
    if alignment in {"left", "justified", "justified-with-no-hyphenation"}:
        typo["alignment"] = alignment
    header_alignment = style.get("headerAlignment")
    if header_alignment in {"left", "center", "right"}:
        header["alignment"] = header_alignment
    title = style.get("sectionTitle")
    allowed_titles = {
        "with_full_line",
        "with_partial_line",
        "without_line",
        "centered_without_line",
        "centered_with_partial_line",
        "centered_with_centered_partial_line",
        "centered_with_full_line",
    }
    if title in allowed_titles:
        titles["type"] = title
    order = style.get("sections")
    cv = merged.get("cv") or {}
    current = cv.get("sections") or {}
    if isinstance(order, list) and isinstance(current, dict):
        ordered: dict[str, Any] = {}
        for key in order:
            name = str(key)
            if name in current:
                ordered[name] = current[name]
        for name, value in current.items():
            if name not in ordered:
                ordered[name] = value
        cv["sections"] = ordered
    return merged


def apply_page_size(merged: dict[str, Any], page_size: str) -> dict[str, Any]:
    key = (page_size or "letter").strip().lower()
    if key not in PAGE_SIZES:
        raise MergeError(["Paper size must be a4 or letter."])
    design = merged.setdefault("design", {})
    page = design.setdefault("page", {})
    page["size"] = PAGE_SIZES[key]
    return merged


def pdf_filename(name: str, position: str, company: str, date_iso: str) -> str:
    parts = [slug_part(name), slug_part(position), slug_part(company), date_iso]
    missing = [
        label
        for label, part in zip(
            ("name", "position", "company", "date"), parts, strict=True
        )
        if not part
    ]
    if missing:
        raise MergeError([f"Missing filename part: {', '.join(missing)}."])
    return "_".join(parts) + ".pdf"
