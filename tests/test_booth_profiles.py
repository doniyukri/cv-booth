from pathlib import Path

import pytest

from booth.merge import MergeError
from booth.profiles import (
    create_profile,
    get_profile,
    list_profiles,
    resolve_active,
    save_master,
    set_active,
    starter_master,
    validate_master_text,
)
from booth.prompt import cv_name, master_prompt, tailor_prompt


def _paths(tmp_path: Path) -> dict[str, Path]:
    master = tmp_path / "master.yaml"
    master.write_text(
        "cv:\n  name: Sample Candidate\ndesign:\n  theme: harvard\n", encoding="utf-8"
    )
    return {
        "profiles_dir": tmp_path / "profiles",
        "default_master": master,
        "default_applications": tmp_path / "applications",
    }


class TestListProfiles:
    def test_includes_the_built_in_master_without_copying_it(
        self, tmp_path: Path
    ) -> None:
        paths = _paths(tmp_path)
        profiles = list_profiles(**paths)
        assert [profile.id for profile in profiles] == ["default"]
        assert profiles[0].master_path == paths["default_master"]
        assert profiles[0].name == "Sample Candidate"
        assert not paths["profiles_dir"].exists()


class TestCreateProfile:
    def test_writes_a_separate_master_for_the_new_name(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        created = create_profile("Ada Lovelace", **paths)
        assert created.id == "ada_lovelace"
        assert created.master_path.is_file()
        assert "Ada Lovelace" in created.master_path.read_text(encoding="utf-8")
        assert (
            paths["default_master"]
            .read_text(encoding="utf-8")
            .startswith("cv:\n  name: Sample")
        )
        assert [profile.id for profile in list_profiles(**paths)] == [
            "default",
            "ada_lovelace",
        ]

    def test_rejects_a_blank_name(self, tmp_path: Path) -> None:
        with pytest.raises(MergeError) as caught:
            create_profile("   ", **_paths(tmp_path))
        assert "name" in caught.value.errors[0].lower()

    def test_adds_a_suffix_when_the_folder_exists(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        create_profile("Ada Lovelace", **paths)
        second = create_profile("Ada Lovelace", **paths)
        assert second.id == "ada_lovelace_2"


class TestGetProfile:
    def test_rejects_an_unknown_id(self, tmp_path: Path) -> None:
        with pytest.raises(MergeError) as caught:
            get_profile("missing", **_paths(tmp_path))
        assert "missing" in caught.value.errors[0]


class TestResolveActive:
    def test_uses_default_when_nothing_is_selected(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        assert resolve_active(**paths).id == "default"

    def test_falls_back_when_the_saved_id_is_gone(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        paths["profiles_dir"].mkdir()
        (paths["profiles_dir"] / "active.txt").write_text("missing\n", encoding="utf-8")
        assert resolve_active(**paths).id == "default"

    def test_switches_to_a_created_profile(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        created = create_profile("Ada Lovelace", **paths)
        selected = set_active(created.id, **paths)
        assert selected.id == "ada_lovelace"
        assert resolve_active(**paths).id == "ada_lovelace"


class TestSaveMaster:
    def test_rejects_a_job_slice_and_leaves_the_file(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        created = create_profile("Ada Lovelace", **paths)
        before = created.master_path.read_text(encoding="utf-8")
        with pytest.raises(MergeError) as caught:
            save_master(created, "position: Engineer\ncompany: Example\n")
        assert "cv" in caught.value.errors[0].lower()
        assert created.master_path.read_text(encoding="utf-8") == before

    def test_writes_only_the_selected_master(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        created = create_profile("Ada Lovelace", **paths)
        saved = save_master(created, starter_master("Ada Lovelace"))
        assert "Ada Lovelace" in saved
        assert created.master_path.read_text(encoding="utf-8") == saved
        assert "Sample Candidate" in paths["default_master"].read_text(encoding="utf-8")


class TestValidateMasterText:
    def test_accepts_the_starter_document(self) -> None:
        text = validate_master_text(starter_master("Ada Lovelace"))
        assert "name: Ada Lovelace" in text

    @pytest.mark.parametrize("fence", ["```", "~~~", "````"])
    def test_accepts_fenced_master_yaml(self, fence: str) -> None:
        master = starter_master("Ada Lovelace")
        text = validate_master_text(f"{fence}yaml\n{master}{fence}")
        assert text == master


class TestMasterPrompt:
    def test_names_the_person_and_asks_for_a_full_cv(self) -> None:
        prompt = master_prompt("Ada Lovelace")
        assert "Ada Lovelace" in prompt
        assert "Do not invent" in prompt
        assert "theme: harvard" in prompt
        assert "position or company" in prompt
        assert "+12025550100" in prompt
        assert "+15555550100" not in prompt

    def test_tailor_prompt_uses_the_cv_name(self) -> None:
        prompt = tailor_prompt({"cv": {"name": "Ada Lovelace", "sections": {}}})
        assert prompt.startswith("You are tailoring Ada Lovelace's CV")
        assert cv_name({}) == "the candidate"
