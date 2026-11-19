"""Parse real generated examples rather than checking their appearance alone."""

import re

from ruamel.yaml import YAML

from booth.merge import ALLOWED_KEYS
from booth.prompt import density_guidance, tailor_prompt


def test_generated_examples_have_valid_nested_yaml_and_consistent_order() -> None:
    master = {
        "cv": {
            "name": "Example Candidate",
            "social_networks": [{"network": "GitHub", "username": "example"}],
            "sections": {
                "education": [
                    {"institution": "Example University", "area": "Computing"}
                ],
                "profile": ["Known facts."],
                "experience": [
                    {
                        "company": "Example Employer",
                        "position": "Engineer",
                        "highlights": ["Built applications."],
                    }
                ],
                "skills": [{"label": "Programming", "details": "Python"}],
                "languages": [{"label": "English", "details": "Professional"}],
            },
        }
    }
    prompt = tailor_prompt(master)
    blocks = re.findall(r"^```yaml\n(.*?)^```", prompt, flags=re.M | re.S)
    assert len(blocks) == 2
    expected = ["profile", "experience", "skills", "education", "languages"]
    for block in blocks:
        data = YAML(typ="safe", pure=True).load(block)
        assert isinstance(data["experience"][0]["highlights"], list)
        assert data["social_networks"][0]["username"]
        assert data["education"][0]["area"]
        assert [key for key in data if key in expected] == expected
        assert [key for key in ALLOWED_KEYS if key in expected] == expected
        for line in block.splitlines():
            assert "\t" not in line
            assert (len(line) - len(line.lstrip(" "))) % 2 == 0
    example = YAML(typ="safe", pure=True).load(blocks[0])
    assert list(example) == list(ALLOWED_KEYS)


def test_equal_roles_leave_the_primary_role_selection_to_job_relevance() -> None:
    master = {
        "cv": {
            "sections": {
                "experience": [
                    {"company": "Example Alpha", "highlights": ["Built interfaces."]},
                    {"company": "Example Beta", "highlights": ["Built APIs."]},
                ]
            }
        }
    }
    guidance = density_guidance(master)
    assert "primary/most relevant role" in guidance
    assert "8-10 relevant bullets for Example Alpha" not in guidance
    assert "8-10 relevant bullets for Example Beta" not in guidance
