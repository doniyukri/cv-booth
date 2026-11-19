"""Local HTTP booth: paste tailor YAML, download a one-page PDF."""

# Imports follow the sys.path insert below so this file can run as a script.
# ruff: noqa: E402

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import asdict
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from ruamel.yaml import YAML

from booth.applications import list_applications
from booth.design import apply_design_defaults
from booth.merge import (
    MergeError,
    application_meta,
    apply_design,
    apply_page_size,
    merge_slice,
    parse_slice,
    pdf_filename,
    slug_part,
    style_from_master,
)
from booth.profiles import (
    create_profile,
    get_profile,
    profile_snapshot,
    resolve_active,
    save_master,
    set_active,
)
from booth.prompt import dump_yaml, master_prompt, tailor_prompt
from rendercv.exception import RenderCVUserError, RenderCVUserValidationError
from rendercv.renderer.pdf_png import generate_pdf, generate_png
from rendercv.renderer.typst import generate_typst
from rendercv.schema.rendercv_model_builder import build_rendercv_dictionary_and_model

DATA_DIR = (
    Path(os.environ.get("CVBOOTH_DATA_DIR") or ROOT / "data").expanduser().resolve()
)
MASTER_PATH = DATA_DIR / "master.yaml"
APPLICATIONS_DIR = DATA_DIR / "applications"
STATIC_DIR = Path(__file__).resolve().parent / "static"
PROFILES_DIR = DATA_DIR / "profiles"
TMP_DIR = DATA_DIR / ".tmp"
SAMPLE_PATH = ROOT / "examples" / "sample-master.yaml"
HOST = "127.0.0.1"
PORT = 8765
_last_job: dict[str, Any] | None = None


def profile_paths() -> dict[str, Path]:
    return {
        "profiles_dir": PROFILES_DIR,
        "default_master": MASTER_PATH,
        "default_applications": APPLICATIONS_DIR,
    }


def current_profile() -> Any:
    return resolve_active(**profile_paths())


def profile_from_id(profile_id: str) -> Any:
    """Resolve the profile a page named. Do not fall back to whoever is active."""
    if not profile_id:
        raise MergeError(["Profile id is required."])
    return get_profile(profile_id, **profile_paths())


def profile_from_query(raw_path: str) -> Any:
    profile_id = (parse_qs(urlparse(raw_path).query).get("id") or [""])[0]
    if profile_id:
        return get_profile(profile_id, **profile_paths())
    return current_profile()


def load_master(profile: Any | None = None) -> dict[str, Any]:
    path = (profile or current_profile()).master_path
    if not path.is_file():
        raise MergeError([f"Master YAML is missing: {path.name}"])
    yaml = YAML(typ="safe", pure=True)
    data = yaml.load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise MergeError(["Master YAML is missing or invalid."])
    return apply_design_defaults(data)


def format_rendercv_errors(exc: RenderCVUserValidationError) -> list[str]:
    messages: list[str] = []
    for error in exc.validation_errors:
        location = ""
        if error.schema_location:
            location = " at " + ".".join(str(part) for part in error.schema_location)
        messages.append(f"{error.message}{location}")
    return messages or ["RenderCV rejected the YAML."]


def job_cache_key(
    paste: str,
    page_size: str,
    style: Any,
    profile_id: str,
    master_text: str,
) -> str:
    style_blob = json.dumps(style or {}, sort_keys=True, default=str)
    master_stamp = hashlib.sha256(master_text.encode("utf-8")).hexdigest()
    return hashlib.sha256(
        f"{profile_id}\n{master_stamp}\n{page_size}\n{style_blob}\n{paste}".encode()
    ).hexdigest()


def prepare_job(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], str, str, str, str, str, str]:
    paste = str(payload.get("yaml") or "")
    page_size = str(payload.get("page_size") or "a4")
    profile = profile_from_id(str(payload.get("profile_id") or ""))
    if not profile.master_path.is_file():
        raise MergeError([f"Master YAML is missing: {profile.master_path.name}"])
    master_text = profile.master_path.read_text(encoding="utf-8")
    yaml = YAML(typ="safe", pure=True)
    master = yaml.load(master_text)
    if not isinstance(master, dict):
        raise MergeError(["Master YAML is missing or invalid."])
    if paste.strip():
        slice_data = parse_slice(paste)
        position, company = application_meta(slice_data)
    else:
        slice_data = {}
        position, company = "Preview", "Master"
    merged = merge_slice(apply_design_defaults(master), slice_data)
    apply_design(merged, payload.get("style"))
    apply_page_size(merged, page_size)
    name = str(merged.get("cv", {}).get("name") or "")
    filename = pdf_filename(name, position, company, date.today().isoformat())
    return (
        merged,
        filename,
        page_size,
        position,
        company,
        job_cache_key(
            paste,
            page_size,
            payload.get("style"),
            profile.id,
            master_text,
        ),
        str(profile.applications_dir),
    )


def render_job(merged: dict[str, Any]) -> tuple[bytes, list[bytes]]:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=TMP_DIR) as tmp:
        tmp_path = Path(tmp)
        yaml_path = tmp_path / "cv.yaml"
        yaml_path.write_text(dump_yaml(merged), encoding="utf-8")
        try:
            _, model = build_rendercv_dictionary_and_model(
                yaml_path.read_text(encoding="utf-8"),
                input_file_path=yaml_path,
                output_folder=tmp_path / "out",
                pdf_path=tmp_path / "out" / "cv.pdf",
                dont_generate_html=True,
                dont_generate_markdown=True,
            )
        except RenderCVUserValidationError as exc:
            raise MergeError(format_rendercv_errors(exc)) from exc
        except RenderCVUserError as exc:
            raise MergeError([exc.message or "RenderCV failed."]) from exc

        typst_path = generate_typst(model)
        pdf_path = generate_pdf(model, typst_path)
        png_paths = generate_png(model, typst_path)
        if pdf_path is None or not pdf_path.exists():
            raise MergeError(["RenderCV did not produce a PDF."])
        if not png_paths:
            raise MergeError(["RenderCV did not produce a page preview."])
        return pdf_path.read_bytes(), [path.read_bytes() for path in png_paths]


def save_application(job: dict[str, Any]) -> Path:
    directory = Path(job["applications_dir"])
    directory.mkdir(parents=True, exist_ok=True)
    stem = job["archive_stem"]
    pdf_path = directory / f"{stem}.pdf"
    n = 2
    while pdf_path.exists():
        pdf_path = directory / f"{stem}-{n}.pdf"
        n += 1
    pdf_path.write_bytes(job["pdf"])
    pdf_path.with_suffix(".yaml").write_text(job["merged_yaml"], encoding="utf-8")
    log_line = (
        f"{datetime.now().isoformat(timespec='seconds')}\t"
        f"{job['company']}\t{job['position']}\t{pdf_path.name}\n"
    )
    with (directory / "log.txt").open("a", encoding="utf-8") as log:
        log.write(log_line)
    return pdf_path


def run_or_recall(payload: dict[str, Any]) -> dict[str, Any]:
    global _last_job  # noqa: PLW0603
    (
        merged,
        filename,
        page_size,
        position,
        company,
        key,
        applications_dir,
    ) = prepare_job(payload)
    if _last_job and _last_job["key"] == key:
        return _last_job
    pdf_bytes, pngs = render_job(merged)
    day = date.today().isoformat()
    _last_job = {
        "key": key,
        "filename": filename,
        "page_size": "letter" if page_size in {"letter", "us-letter"} else "a4",
        "pages": len(pngs),
        "pdf": pdf_bytes,
        "pngs": pngs,
        "position": position,
        "company": company,
        "archive_stem": f"{day}_{slug_part(company)}_{slug_part(position)}",
        "merged_yaml": dump_yaml(merged),
        "applications_dir": applications_dir,
    }
    return _last_job


class BoothHandler(BaseHTTPRequestHandler):
    server_version = "CVBooth/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(
            "%s - %s\n" % (self.address_string(), format % args)  # noqa: UP031
        )

    def _send(
        self,
        status: int,
        body: bytes,
        content_type: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            html = (STATIC_DIR / "index.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path in {"/style", "/style.html"}:
            html = (STATIC_DIR / "style.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/app.css":
            css = (STATIC_DIR / "app.css").read_bytes()
            self._send(200, css, "text/css; charset=utf-8")
            return
        if path == "/profile.js":
            script = (STATIC_DIR / "profile.js").read_bytes()
            self._send(200, script, "text/javascript; charset=utf-8")
            return
        if path == "/theme.js":
            script = (STATIC_DIR / "theme.js").read_bytes()
            self._send(200, script, "text/javascript; charset=utf-8")
            return
        if path == "/properties.js":
            script = (STATIC_DIR / "properties.js").read_bytes()
            self._send(200, script, "text/javascript; charset=utf-8")
            return
        if path == "/api/profiles":
            self._send_json(200, profile_snapshot(**profile_paths()))
            return
        if path == "/api/master":
            try:
                profile = profile_from_query(self.path)
                yaml_text = profile.master_path.read_text(encoding="utf-8")
            except MergeError as exc:
                self._send_json(400, {"errors": exc.errors})
                return
            except OSError as exc:
                self._send_json(500, {"errors": [str(exc)]})
                return
            self._send_json(
                200,
                {"id": profile.id, "name": profile.name, "yaml": yaml_text},
            )
            return
        if path == "/api/master-prompt":
            try:
                prompt = master_prompt(profile_from_query(self.path).name)
            except MergeError as exc:
                self._send_json(400, {"errors": exc.errors})
                return
            except Exception as exc:
                self._send_json(500, {"errors": [str(exc)]})
                return
            self._send_json(200, {"prompt": prompt})
            return
        if path == "/api/prompt":
            try:
                prompt = tailor_prompt(load_master(profile_from_query(self.path)))
            except MergeError as exc:
                self._send_json(400, {"errors": exc.errors})
                return
            except Exception as exc:
                self._send_json(500, {"errors": [str(exc)]})
                return
            self._send_json(200, {"prompt": prompt})
            return
        if path == "/api/style":
            try:
                style = style_from_master(load_master(profile_from_query(self.path)))
                self._send_json(200, {"style": style})
            except MergeError as exc:
                self._send_json(400, {"errors": exc.errors})
            except Exception as exc:
                self._send_json(500, {"errors": [str(exc)]})
            return
        if path == "/api/applications":
            try:
                profile = profile_from_query(self.path)
            except MergeError as exc:
                self._send_json(400, {"errors": exc.errors})
                return
            rows = list_applications(profile.applications_dir / "log.txt")
            self._send_json(200, {"applications": [asdict(row) for row in rows]})
            return
        self._send_json(404, {"errors": ["Not found."]})

    def _read_json(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"errors": ["Request body must be JSON."]})
            return None
        if not isinstance(payload, dict):
            self._send_json(400, {"errors": ["Request body must be a JSON object."]})
            return None
        return payload

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path in {"/api/profiles", "/api/profiles/select", "/api/master"}:
            payload = self._read_json()
            if payload is None:
                return
            try:
                if path == "/api/profiles":
                    created = create_profile(
                        str(payload.get("name") or ""), **profile_paths()
                    )
                    set_active(created.id, **profile_paths())
                elif path == "/api/profiles/select":
                    set_active(str(payload.get("id") or ""), **profile_paths())
                else:
                    profile = profile_from_id(str(payload.get("id") or ""))
                    saved = save_master(profile, str(payload.get("yaml") or ""))
                    fresh = get_profile(profile.id, **profile_paths())
                    self._send_json(
                        200,
                        {"id": fresh.id, "name": fresh.name, "yaml": saved},
                    )
                    return
            except MergeError as exc:
                self._send_json(400, {"errors": exc.errors})
                return
            except Exception as exc:
                self._send_json(500, {"errors": [f"Unexpected error: {exc}"]})
                return
            self._send_json(200, profile_snapshot(**profile_paths()))
            return
        if path not in {"/api/render", "/api/preview"}:
            self._send_json(404, {"errors": ["Not found."]})
            return
        payload = self._read_json()
        if payload is None:
            return

        try:
            job = run_or_recall(payload)
        except MergeError as exc:
            self._send_json(400, {"errors": exc.errors})
            return
        except Exception as exc:
            self._send_json(500, {"errors": [f"Unexpected error: {exc}"]})
            return

        headers = {
            "X-Filename": job["filename"],
            "X-Page-Size": job["page_size"],
            "X-Page-Count": str(job["pages"]),
        }
        if path == "/api/preview":
            self._send_json(
                200,
                {
                    "pages": [
                        base64.b64encode(png).decode("ascii") for png in job["pngs"]
                    ],
                    "pageCount": job["pages"],
                    "pageSize": job["page_size"],
                    "filename": job["filename"],
                },
            )
            return
        if job["pages"] != 1:
            self._send_json(
                400,
                {
                    "errors": [
                        f"Rendered {job['pages']} pages. The proof shows every page. "
                        "Shorten content or switch paper size before downloading."
                    ]
                },
            )
            return
        archive_path = save_application(job)
        headers["X-Archive"] = archive_path.name
        self._send(
            200,
            job["pdf"],
            "application/pdf",
            {
                **headers,
                "Content-Disposition": f'attachment; filename="{job["filename"]}"',
            },
        )


def initialize_data() -> None:
    """Create a local editable sample without overwriting an existing CV."""
    if not MASTER_PATH.exists():
        MASTER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with MASTER_PATH.open("x", encoding="utf-8") as master:
            master.write(SAMPLE_PATH.read_text(encoding="utf-8"))
    TMP_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    initialize_data()
    httpd = ThreadingHTTPServer((HOST, PORT), BoothHandler)
    print(f"CV booth: http://{HOST}:{PORT}")  # noqa: T201
    print(f"Master:   {MASTER_PATH}")  # noqa: T201
    print("Ctrl+C to stop.")  # noqa: T201
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")  # noqa: T201
        httpd.server_close()


if __name__ == "__main__":
    main()
