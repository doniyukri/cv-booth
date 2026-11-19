"""Shared CV layout defaults, separate from personal CV content."""

from copy import deepcopy
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


def default_design() -> dict[str, Any]:
    """Return the reusable A4 Harvard layout without candidate data."""
    return YAML(typ="safe", pure=True).load(
        Path(__file__).with_name("default-design.yaml").read_text(encoding="utf-8")
    )


def apply_design_defaults(document: dict[str, Any]) -> dict[str, Any]:
    """Fill missing layout settings while keeping explicit user choices."""
    merged = deepcopy(document)

    def overlay(base: dict[str, Any], custom: dict[str, Any]) -> dict[str, Any]:
        for key, value in custom.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = overlay(base[key], value)
            else:
                base[key] = deepcopy(value)
        return base

    merged["design"] = overlay(default_design(), merged.get("design") or {})
    return merged
