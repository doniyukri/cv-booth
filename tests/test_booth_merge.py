"""Validate AI response wrappers without weakening the YAML contract."""

import pytest

from booth.merge import MergeError, parse_slice


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
