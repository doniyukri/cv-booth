"""Build provider-independent AI prompts from the current master CV."""

from __future__ import annotations

from io import StringIO
from typing import Any

from ruamel.yaml import YAML

from booth.merge import ALLOWED_KEYS, master_slice


def dump_yaml(data: Any) -> str:
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 88
    yaml.indent(mapping=2, sequence=4, offset=2)
    buf = StringIO()
    yaml.dump(data, buf)
    return buf.getvalue().rstrip() + "\n"


def cv_name(master: dict[str, Any]) -> str:
    cv = master.get("cv")
    if isinstance(cv, dict):
        name = str(cv.get("name") or "").strip()
        if name:
            return name
    return "the candidate"


def master_prompt(name: str) -> str:
    """Instructions any AI assistant can follow to write a full master CV."""
    person = name.strip() or "the candidate"
    return f"""You are helping {person} write a RenderCV master CV.

This is the full career document, not a one-job tailor. If this chat does not already contain their background, ask for it in one message: name, city, email, phone with country code, website, jobs (company, title, dates, bullets), education, skills, and languages. Do not invent employers, dates, degrees, or numbers. Omit any fact you do not have.

When the background is in the chat, return YAML ONLY. No markdown fences. No commentary.

The document has two top-level keys, cv and design.

cv:
- name: the person's name
- headline: a short role title, or omit it
- location, email, phone, website: omit any you do not have
- phone uses a country code, such as +62
- social_networks: a list of {{network, username}} when known. network is LinkedIn or GitHub
- sections.profile: a YAML list with exactly one summary paragraph
- sections.experience: a YAML list. Each job has company, position, start_date, end_date, and highlights (list of strings). Dates are YYYY, YYYY-MM, or present
- sections.education: institution, area, degree, location, start_date, end_date, highlights
- sections.skills: a YAML list of {{label, details}} one-liners
- sections.languages: a YAML list of {{label, details}} one-liners, one language per row
- Markdown in strings may use **bold** and [links](https://example.com)
- Do not add position or company. Those belong to a later job paste, not the master
- Do not add empty sections

design:
- theme: harvard
- page.size: us-letter

Use this shape, dropping any block you cannot fill from the chat:

cv:
  name: {person}
  headline: Role title
  location: City, Country
  email: name@example.com
  phone: "+12025550100"
  website: https://example.com
  social_networks:
    - network: LinkedIn
      username: example
    - network: GitHub
      username: example
  sections:
    profile:
      - One paragraph summary.
    experience:
      - company: Example
        position: Role
        start_date: 2022-08
        end_date: present
        highlights:
          - Bullet from their real work
    education:
      - institution: Example University
        area: Field
        degree: Bachelor's
        location: City, Country
        start_date: 2014
        end_date: 2018
    skills:
      - label: Group
        details: Tool, Tool
    languages:
      - label: Language
        details: Level
design:
  theme: harvard
  page:
    size: us-letter
"""


def tailor_prompt(master: dict[str, Any]) -> str:
    """Build a self-contained tailoring contract for any AI assistant."""
    allowed = ", ".join(ALLOWED_KEYS)
    slice_yaml = dump_yaml(master_slice(master))
    name = cv_name(master)
    return f"""You are tailoring {name}'s CV for ONE job posting.

Return YAML ONLY. No markdown fences. No commentary. No design, locale, or settings.

Required top-level keys (always include):
- position: the job title being applied for (used to name the PDF; not printed on the CV)
- company: the company being applied to (used to name the PDF; not printed on the CV)

Optional content keys (omit any you are not changing): headline, profile, experience, skills, languages

Allowed keys: {allowed}

Rules:
- Do not include cv:, design:, locale:, settings:, name, email, phone, location, website, social_networks, or education.
- Extra keys are rejected by the renderer.
- headline: a short string (job-facing title on the CV).
- profile: a YAML list with exactly one string (the summary paragraph).
- experience: a YAML list of jobs. Each job MUST have company, position, start_date, end_date, and highlights (list of strings). Dates are YYYY, YYYY-MM, or present.
- skills: a YAML list of {{label, details}} one-liners.
- languages: a YAML list of {{label, details}} one-liners (e.g. Indonesian / Native, English / Professional). Usually omit this key so the master languages stay.
- If you send a content key, send the FULL replacement for that section (whole-section replace). Omitted content keys keep the master.
- Use only facts in the master slice. Do not invent employers, dates, qualifications, or numbers.
- Target ONE page. Prefer fewer, sharper bullets over more bullets. Do not add sections.

Use the job description supplied with this prompt to rewrite the slice below. Always set position and company from that job. If the job description, job title, or company is missing, ask for the missing information before generating YAML.

Current master slice:
```yaml
{slice_yaml.rstrip()}
```
"""
