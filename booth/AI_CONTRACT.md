# AI tailor contract

The local booth copies a **live** version of this prompt (schema + current master slice) via **Copy AI prompt**. Paste it into your preferred AI assistant with the job description, then paste the response back into the booth. This file is the standing contract. There is no provider account, API key, or model configuration in the booth.

## What the AI assistant may return

The copied AI prompt requests a single `yaml` code block with no commentary, strict 2-space indentation, and double-quoted string values (including dates and phone numbers).

The booth also accepts a single YAML code block enclosed in backticks or tildes, with an optional `yaml` or `yml` language tag. Commentary and multiple blocks are rejected. Model output must still pass the same schema and page-count checks.

**Required** (always include; used to name the PDF, not printed on the CV):

- `position` — job title you are applying for
- `company` — company you are applying to

**Content keys** (the AI prompt asks for all of these, copying unchanged master facts):

- `name`
- `location`
- `email`
- `phone`
- `website`
- `social_networks`
- `headline`
- `profile`
- `experience`
- `skills`
- `education`
- `languages`

Put these keys at the top level. Do **not** wrap them in `cv:` or send `design:`, `locale:`, or `settings:`.

Contact fields and education can override the master for this PDF. The master file is not changed. Preserve factual contact details and qualifications unless the user explicitly supplies an update. Use `null` for unknown contact fields and `[]` for unknown lists, never invented values or placeholders. Manually entered partial slices remain supported; omitted keys keep the master.

## Content and density guidance

- Keep the headline to the target job title, without a pipe-separated technology stack.
- Aim for a full single A4 page, about four profile sentences, and five concise skills rows when the source supports them.
- Role-specific targets are derived from the current master: about three bullets for project roles and eight to ten for the primary/most relevant role when enough distinct, verified achievements exist. When there are multiple employers, choose by job relevance rather than existing bullet count.
- Never inject unverified job-description keywords or claims. Do not invent or repeat facts to meet a count or fill whitespace.
- Keep GPA inside `education[].highlights`; do not add a `gpa` key.
- Use the renderer's preview to check real pagination and adjust relevant content accordingly.

## Merge rules (enforced by the booth)

- Omitted key → keep the master.
- Present contact or headline key → replace that field.
- Present list key → replace the whole list (including `social_networks` and `education`).
- Extra keys → hard fail, no PDF.
- Invalid YAML or RenderCV schema errors → hard fail.
- PDF longer than one page in the selected paper size → download blocked; preview shows every page.

## Entry shapes

```yaml
position: Frontend Engineer
company: GoTo
name: Sample Candidate
location: Example City
email: sample@example.com
phone: "+12025550100"
website: https://example.com
social_networks:
  - network: LinkedIn
    username: example
headline: Frontend Engineer
profile:
  - One summary paragraph.
experience:
  - company: Example
    position: Frontend Engineer
    start_date: 2022-08
    end_date: present
    highlights:
      - Bullet
skills:
  - label: Frontend
    details: Vue.js, React.js, Next.js
education:
  - institution: Example University
    area: Computer Science
    degree: BS
    start_date: 2018
    end_date: 2022
languages:
  - label: Indonesian
    details: Native
  - label: English
    details: Professional
```

Dates: `YYYY`, `YYYY-MM`, or `present`.
