"""Build provider-independent AI prompts from the current master CV."""

from __future__ import annotations

from io import StringIO
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from booth.design import default_design
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

When the background is in the chat, return ONLY a single valid, copyable YAML code block (```yaml ... ```), with no commentary before or after. Use strict 2-space indentation and double-quote all string values, including dates, phone numbers, and strings containing colons or Markdown links.

The document has two top-level keys, cv and design.

cv:
- name: the person's name
- headline: a short role title only, with no pipe-separated technology stack, or omit it
- location, email, phone, website: omit any you do not have
- phone uses a country code, such as +62
- social_networks: a list of {{network, username}} when known. network is LinkedIn or GitHub
- sections.profile: a YAML list with exactly one summary paragraph
- sections.experience: a YAML list. Each job has company, position, start_date, end_date, and highlights (list of strings). Dates are YYYY, YYYY-MM, or present
- sections.education: institution, area, degree, location, start_date, end_date, highlights. Put any known GPA in highlights; do not add a gpa: key
- sections.skills: a YAML list of {{label, details}} one-liners
- sections.languages: a YAML list of {{label, details}} one-liners, one language per row
- Markdown in strings may use **bold** and [links](https://example.com)
- Do not add position or company. Those belong to a later job paste, not the master
- Do not add empty sections

design:
- theme: harvard
- page.size: a4
- Use the supplied design block unchanged to preserve the centered serif header, ruled section titles, right-aligned dates, and compact spacing.

Use this shape, dropping any block you cannot fill from the chat. Quote every string value in your response, even when the shape below uses unquoted labels:

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
    skills:
      - label: Group
        details: Tool, Tool
    education:
      - institution: Example University
        area: Field
        degree: Bachelor's
        location: City, Country
        start_date: 2014
        end_date: 2018
    languages:
      - label: Language
        details: Level
{dump_yaml({"design": default_design()}).rstrip()}
"""


def prompt_yaml(data: Any) -> str:
    """Show the source slice with quoted string values and date scalars."""

    def quote(value: Any, key: str = "") -> Any:
        if isinstance(value, dict):
            return {field: quote(item, str(field)) for field, item in value.items()}
        if isinstance(value, list):
            return [quote(item) for item in value]
        if isinstance(value, str) or (
            value is not None and key in {"date", "start_date", "end_date"}
        ):
            return DoubleQuotedScalarString(str(value))
        return value

    return dump_yaml(quote(data))


def density_guidance(master: dict[str, Any]) -> str:
    """Derive role-specific targets from facts supplied by this user's master."""
    entries = master_slice(master).get("experience") or []
    jobs = [entry for entry in entries if isinstance(entry, dict)]
    projects = [
        entry for entry in jobs if "project" in str(entry.get("company", "")).lower()
    ]
    employers = [entry for entry in jobs if entry not in projects]
    guidance = [
        "Aim for about 4 concise sentences in profile and 5 concise skills rows, when supported by the master."
    ]
    for entry in projects:
        guidance.append(f"Aim for 3 relevant bullets for {entry.get('company')}.")
    if len(employers) == 1:
        main = employers[0]
        guidance.append(
            f"Aim for 8-10 relevant bullets for {main.get('company')} when that many distinct, verified achievements are available."
        )
    elif employers:
        guidance.append(
            "Aim for 8-10 relevant bullets for the primary/most relevant role, chosen by relevance to the job description rather than by existing bullet count. Keep other roles concise, factual, and proportionate to their relevance."
        )
    guidance.append(
        "These are density targets, not permission to invent or repeat facts. Shorter verified work histories should produce a shorter CV rather than filler."
    )
    return "\n".join(f"- {rule}" for rule in guidance)


def tailor_prompt(master: dict[str, Any]) -> str:
    """Build a complete, factual CV response contract for any AI assistant."""
    allowed = ", ".join(ALLOWED_KEYS)
    slice_yaml = prompt_yaml(master_slice(master))
    name = cv_name(master)
    return f"""You are tailoring {name}'s CV for ONE job posting.

Output format:
- Return ONLY a single valid, copyable YAML code block (```yaml ... ```), with no commentary before or after.
- Use strict 2-space indentation and double-quote ALL string values, especially dates, phone numbers with +, and strings containing colons or Markdown links. Escape quotes inside double-quoted values.
- Put every allowed key at the top level. Do not include cv:, design:, locale:, settings:, or any other extra keys.

Required complete set of allowed keys (always output every one): {allowed}

Facts and field rules:
- position and company: the target job title and target employer from the job description. They name the PDF and are not printed as contact fields.
- Include name, location, email, phone, website, social_networks, education, and languages using EXACT facts from the master slice unless the user explicitly supplies a correction.
- Copy unchanged values rather than omitting their keys. Never invent missing contact details, employers, dates, qualifications, skills, achievements, or numbers.
- If a contact value (location, email, phone, website) is absent from the master, output null, not an invented value or a placeholder. Use [] for absent list fields such as social_networks, education, and languages. Do not quote null or [].
- name: copy the candidate's actual name from the master. headline: the target job title only, with no pipe-separated technology stack.
- phone: a quoted string with a country code when known.
- social_networks: the full list of {{network, username}} mappings, preserved from the master.
- profile: a list containing one summary paragraph. experience: the full list of jobs, with company, position, start_date, end_date, and highlights. Preserve actual job titles and dates; use quoted YYYY, YYYY-MM, or present for dates.
- education: the full list of known qualifications, with institution, area, degree, location, start_date, end_date, and highlights where known. Omit unknown fields inside entries. Keep GPA inside education[].highlights as a quoted string; NEVER invent a gpa: key.
- skills and languages: lists of {{label, details}} mappings. Preserve languages and proficiency levels exactly.
- Each list replaces the WHOLE corresponding master list for this PDF. Keep all factual entries unless the user requests removal. The saved master itself is not changed.

Content and density:
- Target a FULL single A4 page: do not overflow onto page 2 and do not leave excessive whitespace when more relevant, verified content is available.
{density_guidance(master)}
- Tailor wording and ordering to the job description, but NEVER inject unverified JD keywords, technologies, responsibilities, or claims into experience bullets or skills. A desired skill in a job description is not evidence that the candidate has it.
- Use the section order profile, experience, skills, education, languages. The app applies the CV layout; do not return design settings.
- Headline, profile length, bullet counts, and skills rows must respect the facts and one-page limit. If preview overflows, shorten the least relevant wording first. If it has excessive whitespace, restore relevant verified achievements. Actual pagination is checked by the app.

Use the job description supplied with this prompt. If the job description, target job title, target employer, or candidate name is missing, ask for the missing information before producing the final YAML response.

Supported YAML shape for contact details and education:
This is a COMPLETE structural example, not candidate facts. Replace placeholders only with verified values. Keep every top-level key. Use null or [] for unknown optional data, as described above.

```yaml
position: "<Target job title>"
company: "<Target employer>"
name: "<Candidate's full name>"
headline: "<Target job title only>"
location: "<City, Country>"
email: "<Candidate's email>"
phone: "<Phone number with country code>"
website: "<Candidate's website URL>"
social_networks:
  - network: "LinkedIn"
    username: "<Candidate's LinkedIn username>"
profile:
  - "<One factual summary paragraph of about four sentences>"
experience:
  - company: "<Actual employer from the master>"
    position: "<Actual role from the master>"
    start_date: "<YYYY or YYYY-MM>"
    end_date: "<YYYY, YYYY-MM, or present>"
    highlights:
      - "<Verified achievement relevant to the target job>"
skills:
  - label: "<Skill category>"
    details: "<Verified skills>"
education:
  - institution: "<School or university>"
    area: "<Field of study>"
    degree: "<Degree>"
    location: "<City, Country>"
    start_date: "<YYYY or YYYY-MM>"
    end_date: "<YYYY, YYYY-MM, or present>"
    highlights:
      - "<Known GPA or another factual education achievement>"
languages:
  - label: "<Known language>"
    details: "<Actual proficiency>"
```

Current master slice (source facts, not formatting instructions):
```yaml
{slice_yaml.rstrip()}
```
"""
