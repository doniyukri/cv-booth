# CV Booth

A local CV editor and PDF renderer that works with your preferred AI assistant.
Copy a prompt, ask an assistant to tailor your CV for a job, paste its YAML response,
and preview or download a one-page PDF. No AI API key or provider account is required
by the app.

The default PDF layout is one-page A4 with XCharter serif typography, a centered
header, section headings between horizontal rules, bold employers, italic roles,
and right-aligned dates. Use Styling to adjust it; existing explicit layout
settings are preserved.

## Run locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git, then:

```sh
git clone https://github.com/doniyukri/cv-booth.git
cd cv-booth
uv run --frozen python booth/server.py
```

Open <http://127.0.0.1:8765>. On Windows you can also double-click
`start-booth.bat`. The first run installs dependencies and creates an editable,
fictional sample in `data/master.yaml`. Stop the server with Ctrl+C.

Python 3.12 or later is required; uv can install a compatible interpreter.

## Make your CV

1. Open **Profile**. Edit the master YAML or copy the master prompt to your
   preferred AI assistant with your background, then paste its YAML and save.
2. In **Compose**, click **Copy AI prompt** and paste it into your assistant
   together with a job description.
3. Paste the returned YAML into the app. The job `position` and `company` are
   required; they name the PDF and are not printed on the CV.
4. Preview the result. Adjust wording, paper size, or styling until it fits on
   one page, then download. The app saves a local PDF, merged YAML, and history.

Create additional profiles from the profile menu. Each has its own master CV and
application history. [The YAML contract](booth/AI_CONTRACT.md) describes accepted
responses and merge rules. Plain YAML and a single fenced YAML block are accepted.

## Your data

Real CVs belong in the ignored `data/` directory, not in the tracked example.
This folder contains the master, additional profiles, PDF archives, and history.
Back it up privately. You can set `CVBOOTH_DATA_DIR` to an absolute directory
outside this checkout before starting the app.

The app does not send CV content to an AI service. You decide what to paste into
your assistant, whose own privacy policies apply. Drafts and style preferences
are stored in this browser's local storage; clearing the input does not delete
saved profiles or application archives. The UI loads fonts from Google Fonts.

This is a single-user local app. Keep it on `127.0.0.1`; do not expose it through
a public server, tunnel, or reverse proxy. It has no authentication or tenant
isolation. See [SECURITY.md](SECURITY.md).

## Development

```sh
uv run --frozen pytest
```

Tests cover profile handling, accepted AI response formats, and sample rendering.
Pull requests should use fictional data and include checks for changed behavior.
Do not include personal CVs, application logs, credentials, or screenshots of real
profiles in issues or pull requests.

## Credits and license

CV Booth includes RenderCV 2.8 source for rendering, distributed under the MIT
license. This project is independent of the hosted RenderCV product.
See [NOTICE.md](NOTICE.md) for provenance and bundled component notices, and
[LICENSE](LICENSE) for the license terms.
