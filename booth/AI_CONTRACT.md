# AI tailor contract

The local booth copies a **live** version of this prompt (schema + current master slice) via **Copy AI prompt**. Paste it into your preferred AI assistant with the job description, then paste the response back into the booth. This file is the standing contract. There is no provider account, API key, or model configuration in the booth.

## What the AI assistant may return

YAML only. No markdown fences. No commentary.

The booth also accepts a single YAML code block enclosed in backticks or tildes, with an optional `yaml` or `yml` language tag. Commentary and multiple blocks are rejected. Model output must still pass the same schema and page-count checks.

**Required** (always include; used to name the PDF, not printed on the CV):

- `position` — job title you are applying for
- `company` — company you are applying to

**Optional content** (omit any you are not changing):

- `headline`
- `profile`
- `experience`
- `skills`
- `languages`

Do **not** send `cv:`, `design:`, `locale:`, `settings:`, contact fields, or `education`.

## Merge rules (enforced by the booth)

- Omitted key → keep the master.
- Present key → replace that whole section.
- Extra keys → hard fail, no PDF.
- Invalid YAML or RenderCV schema errors → hard fail.
- PDF longer than one page in the selected paper size → download blocked; preview shows every page.

## Entry shapes

```yaml
position: Frontend Engineer
company: GoTo
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
languages:
  - label: Indonesian
    details: Native
  - label: English
    details: Professional
```

Dates: `YYYY`, `YYYY-MM`, or `present`.
