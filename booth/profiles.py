"""Named booth profiles. Each one has its own master CV."""

from __future__ import annotations

import re
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from booth.design import default_design
from booth.merge import MergeError, slug_part, strip_fences
from booth.prompt import dump_yaml
from rendercv.exception import RenderCVUserError, RenderCVUserValidationError
from rendercv.schema.rendercv_model_builder import build_rendercv_dictionary_and_model

DEFAULT_PROFILE_ID = "default"
ACTIVE_FILE = "active.txt"


@dataclass(frozen=True)
class Profile:
    id: str
    name: str
    master_path: Path
    applications_dir: Path


def starter_master(name: str) -> str:
    """A valid RenderCV document with nothing invented beyond the person's name."""
    return dump_yaml(
        {
            "cv": {
                "name": name,
                "sections": {
                    "profile": [
                        "Replace this line with a one-paragraph summary of this person."
                    ],
                },
            },
            "design": default_design(),
        }
    )


def _read_name(path: Path, fallback: str) -> str:
    if not path.exists():
        return fallback
    try:
        data = YAML(typ="safe", pure=True).load(path.read_text(encoding="utf-8"))
    except YAMLError:
        return fallback
    if not isinstance(data, dict):
        return fallback
    cv = data.get("cv")
    if not isinstance(cv, dict):
        return fallback
    name = str(cv.get("name") or "").strip()
    return name or fallback


def _default_profile(default_master: Path, default_applications: Path) -> Profile:
    return Profile(
        id=DEFAULT_PROFILE_ID,
        name=_read_name(default_master, "Sample Candidate"),
        master_path=default_master,
        applications_dir=default_applications,
    )


def list_profiles(
    *,
    profiles_dir: Path,
    default_master: Path,
    default_applications: Path,
) -> list[Profile]:
    """The built-in profile first, then profiles saved under profiles_dir."""
    profiles = [_default_profile(default_master, default_applications)]
    if not profiles_dir.exists():
        return profiles
    folders = sorted(
        path
        for path in profiles_dir.iterdir()
        if path.is_dir() and (path / "master.yaml").is_file()
    )
    for folder in folders:
        profile_id = folder.name
        if profile_id == DEFAULT_PROFILE_ID or not re.fullmatch(
            r"[a-z0-9_]+", profile_id
        ):
            continue
        profiles.append(
            Profile(
                id=profile_id,
                name=_read_name(folder / "master.yaml", profile_id),
                master_path=folder / "master.yaml",
                applications_dir=folder / "applications",
            )
        )
    return profiles


def _active_path(profiles_dir: Path) -> Path:
    return profiles_dir / ACTIVE_FILE


def read_active_id(*, profiles_dir: Path) -> str:
    path = _active_path(profiles_dir)
    if not path.is_file():
        return DEFAULT_PROFILE_ID
    profile_id = path.read_text(encoding="utf-8").strip()
    return profile_id or DEFAULT_PROFILE_ID


def resolve_active(
    *,
    profiles_dir: Path,
    default_master: Path,
    default_applications: Path,
) -> Profile:
    """Return the selected profile. An unknown id falls back to the built-in one."""
    profiles = list_profiles(
        profiles_dir=profiles_dir,
        default_master=default_master,
        default_applications=default_applications,
    )
    wanted = read_active_id(profiles_dir=profiles_dir)
    for profile in profiles:
        if profile.id == wanted:
            return profile
    return profiles[0]


def get_profile(
    profile_id: str,
    *,
    profiles_dir: Path,
    default_master: Path,
    default_applications: Path,
) -> Profile:
    """Return one profile. An unknown id raises instead of falling back."""
    profiles = list_profiles(
        profiles_dir=profiles_dir,
        default_master=default_master,
        default_applications=default_applications,
    )
    match = next((profile for profile in profiles if profile.id == profile_id), None)
    if match is None:
        raise MergeError([f"No profile named {profile_id}."])
    return match


def set_active(
    profile_id: str,
    *,
    profiles_dir: Path,
    default_master: Path,
    default_applications: Path,
) -> Profile:
    match = get_profile(
        profile_id,
        profiles_dir=profiles_dir,
        default_master=default_master,
        default_applications=default_applications,
    )
    profiles_dir.mkdir(parents=True, exist_ok=True)
    _active_path(profiles_dir).write_text(match.id + "\n", encoding="utf-8")
    return match


def _unique_id(name: str, profiles_dir: Path) -> str:
    folded = unicodedata.normalize("NFKD", name)
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    base = re.sub(r"[^a-z0-9_]", "", slug_part(folded).lower()) or "profile"
    if base == DEFAULT_PROFILE_ID:
        base = "profile"
    candidate = base
    number = 2
    while (profiles_dir / candidate).exists():
        candidate = f"{base}_{number}"
        number += 1
    return candidate


def create_profile(
    name: str,
    *,
    profiles_dir: Path,
    default_master: Path,
    default_applications: Path,
) -> Profile:
    """Create a profile and leave the previous master files untouched.

    default_master and default_applications are accepted so callers can pass
    the same path bundle as the other profile functions.
    """
    del default_master, default_applications
    cleaned = " ".join(name.split())
    if not cleaned:
        raise MergeError(["Profile name is required."])
    if len(cleaned) > 80:
        raise MergeError(["Profile name must be 80 characters or fewer."])
    profiles_dir.mkdir(parents=True, exist_ok=True)
    profile_id = _unique_id(cleaned, profiles_dir)
    folder = profiles_dir / profile_id
    folder.mkdir()
    master_path = folder / "master.yaml"
    master_path.write_text(starter_master(cleaned), encoding="utf-8")
    return Profile(
        id=profile_id,
        name=cleaned,
        master_path=master_path,
        applications_dir=folder / "applications",
    )


def profile_snapshot(
    *,
    profiles_dir: Path,
    default_master: Path,
    default_applications: Path,
) -> dict[str, Any]:
    active = resolve_active(
        profiles_dir=profiles_dir,
        default_master=default_master,
        default_applications=default_applications,
    )
    return {
        "active": active.id,
        "profiles": [
            {"id": profile.id, "name": profile.name}
            for profile in list_profiles(
                profiles_dir=profiles_dir,
                default_master=default_master,
                default_applications=default_applications,
            )
        ],
    }


def _rendercv_errors(exc: RenderCVUserValidationError) -> list[str]:
    messages: list[str] = []
    for error in exc.validation_errors:
        location = ""
        if error.schema_location:
            location = " at " + ".".join(str(part) for part in error.schema_location)
        messages.append(f"{error.message}{location}")
    return messages or ["RenderCV rejected the master YAML."]


def validate_master_text(text: str) -> str:
    """Return the text to store, or raise MergeError without writing a master."""
    cleaned = strip_fences(text)
    if not cleaned.strip():
        raise MergeError(["Master YAML is empty."])
    if not cleaned.endswith("\n"):
        cleaned += "\n"
    try:
        data = YAML(typ="safe", pure=True).load(cleaned)
    except YAMLError as exc:
        problem = getattr(exc, "problem", None) or str(exc)
        raise MergeError([f"Master is not valid YAML. {problem}"]) from exc
    if not isinstance(data, dict) or not isinstance(data.get("cv"), dict):
        raise MergeError(["Master YAML must contain a cv: mapping."])
    if not str(data["cv"].get("name") or "").strip():
        raise MergeError(["Master YAML needs cv.name."])
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        yaml_path = tmp_path / "cv.yaml"
        yaml_path.write_text(cleaned, encoding="utf-8")
        try:
            build_rendercv_dictionary_and_model(
                cleaned,
                input_file_path=yaml_path,
                output_folder=tmp_path / "out",
                pdf_path=tmp_path / "out" / "cv.pdf",
                dont_generate_html=True,
                dont_generate_markdown=True,
            )
        except RenderCVUserValidationError as exc:
            raise MergeError(_rendercv_errors(exc)) from exc
        except RenderCVUserError as exc:
            raise MergeError(
                [exc.message or "RenderCV rejected the master YAML."]
            ) from exc
    return cleaned


def save_master(profile: Profile, text: str) -> str:
    """Validate, then replace only this profile's master file."""
    cleaned = validate_master_text(text)
    profile.master_path.parent.mkdir(parents=True, exist_ok=True)
    profile.master_path.write_text(cleaned, encoding="utf-8")
    return cleaned
