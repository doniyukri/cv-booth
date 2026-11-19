"""Validate AI response wrappers without weakening the YAML contract."""

import pytest

from booth.merge import MergeError, master_slice, merge_slice, parse_slice


@pytest.mark.parametrize(
    "wrapper",
    [
        "{yaml}",
        "```\n{yaml}\n```",
        "```yaml\n{yaml}\n```",
        "```yml\n{yaml}\n```",
        "~~~yaml\n{yaml}\n~~~",
        "````YAML\n{yaml}\n````",
    ],
)
def test_reads_tailor_yaml_from_common_response_wrappers(wrapper: str) -> None:
    yaml = "position: Engineer\ncompany: Example\nprofile:\n  - Real experience."
    assert parse_slice(wrapper.format(yaml=yaml)) == {
        "position": "Engineer",
        "company": "Example",
        "profile": ["Real experience."],
    }


@pytest.mark.parametrize(
    "raw",
    [
        "```yaml\nposition: Engineer\ncompany: Example",
        "```yaml\nposition: Engineer\ncompany: Example\n~~~",
        "```yaml\nposition: Engineer\ncompany: Example\n```\nHere is your CV.",
        "```yaml\nposition: Engineer\n```\n```yaml\ncompany: Example\n```",
        "```yaml\nposition: Engineer\ncompany: Example\ncv:\n  name: Invented\n```",
        "```yaml\n- Engineer\n- Example\n```",
    ],
)
def test_rejects_malformed_or_out_of_contract_responses(raw: str) -> None:
    with pytest.raises(MergeError):
        parse_slice(raw)


def test_contact_and_education_overrides_preserve_omitted_master_fields() -> None:
    master = {
        "cv": {
            "name": "Sample Candidate",
            "email": "sample@example.com",
            "location": "Original City",
            "social_networks": [{"network": "GitHub", "username": "original"}],
            "sections": {
                "education": [{"institution": "Original University"}],
                "skills": [{"label": "Languages", "details": "Python"}],
            },
        },
        "design": {"theme": "harvard"},
    }
    override = parse_slice(
        "position: Engineer\ncompany: Example Employer\n"
        "name: Example Person\nemail: person@example.com\n"
        "phone: '+12025550100'\nwebsite: https://example.com\n"
        "social_networks:\n  - network: LinkedIn\n    username: example\n"
        "education:\n  - institution: Example University\n    area: Computing\n"
    )
    merged = merge_slice(master, override)
    assert merged["cv"]["name"] == "Example Person"
    assert merged["cv"]["email"] == "person@example.com"
    assert merged["cv"]["phone"] == "+12025550100"
    assert merged["cv"]["website"] == "https://example.com"
    assert merged["cv"]["location"] == "Original City"
    assert merged["cv"]["social_networks"] == override["social_networks"]
    assert merged["cv"]["sections"]["education"] == override["education"]
    assert merged["cv"]["sections"]["skills"] == master["cv"]["sections"]["skills"]
    assert merged["design"] == master["design"]
    assert "position" not in merged["cv"]
    assert "company" not in merged["cv"]
    assert master["cv"]["name"] == "Sample Candidate"
    assert (
        master["cv"]["sections"]["education"][0]["institution"] == "Original University"
    )
    # The next copied AI prompt should describe every supported field of this CV.
    copied_slice = master_slice(merged)
    assert copied_slice["name"] == "Example Person"
    assert copied_slice["education"] == override["education"]
    assert copied_slice["social_networks"] == override["social_networks"]


def test_explicit_empty_lists_clear_only_the_requested_lists() -> None:
    master = {
        "cv": {
            "name": "Sample Candidate",
            "social_networks": [{"network": "GitHub", "username": "example"}],
            "sections": {
                "education": [{"institution": "Example University"}],
                "profile": ["Keep this summary."],
            },
        }
    }
    merged = merge_slice(master, parse_slice("social_networks: []\neducation: []"))
    assert merged["cv"]["social_networks"] == []
    assert merged["cv"]["sections"]["education"] == []
    assert merged["cv"]["sections"]["profile"] == ["Keep this summary."]
