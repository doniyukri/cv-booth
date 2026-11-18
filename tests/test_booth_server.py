"""Check first-run data isolation and the complete sample rendering pipeline."""

import json
from pathlib import Path
from threading import Thread
from urllib.request import urlopen

import pytest

from booth import server


def configure_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(server, "MASTER_PATH", tmp_path / "data" / "master.yaml")
    monkeypatch.setattr(server, "PROFILES_DIR", tmp_path / "data" / "profiles")
    monkeypatch.setattr(server, "APPLICATIONS_DIR", tmp_path / "data" / "applications")
    monkeypatch.setattr(server, "TMP_DIR", tmp_path / "data" / ".tmp")
    monkeypatch.setattr(server, "_last_job", None)


def test_first_run_creates_a_private_editable_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configure_data(monkeypatch, tmp_path)
    sample = server.SAMPLE_PATH.read_text(encoding="utf-8")
    server.initialize_data()
    assert server.MASTER_PATH.read_text(encoding="utf-8") == sample
    assert server.current_profile().id == "default"
    server.MASTER_PATH.write_text("my private draft", encoding="utf-8")
    server.initialize_data()
    assert server.MASTER_PATH.read_text(encoding="utf-8") == "my private draft"
    assert server.SAMPLE_PATH.read_text(encoding="utf-8") == sample


def test_sample_can_be_tailored_rendered_and_archived(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configure_data(monkeypatch, tmp_path)
    server.initialize_data()
    job = server.run_or_recall(
        {
            "profile_id": "default",
            "page_size": "letter",
            "yaml": "position: Engineer\ncompany: Example Employer\n",
        }
    )
    assert job["pages"] == 1
    assert job["pdf"].startswith(b"%PDF-")
    archived = server.save_application(job)
    assert archived.parent == server.APPLICATIONS_DIR
    assert archived.is_file()
    assert archived.with_suffix(".yaml").is_file()
    assert (server.APPLICATIONS_DIR / "log.txt").is_file()


def test_fresh_server_serves_the_sample_profile_and_ai_prompt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configure_data(monkeypatch, tmp_path)
    server.initialize_data()
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.BoothHandler)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_port}"
    try:
        with urlopen(f"{base}/api/profiles", timeout=5) as response:
            snapshot = json.load(response)
        assert snapshot == {
            "active": "default",
            "profiles": [{"id": "default", "name": "Sample Candidate"}],
        }
        with urlopen(f"{base}/api/prompt?id=default", timeout=5) as response:
            prompt = json.load(response)["prompt"]
        assert "Sample Candidate" in prompt
        assert "Example Company" in prompt
        with urlopen(f"{base}/", timeout=5) as response:
            html = response.read().decode("utf-8")
        assert "Copy AI prompt" in html
        assert "cvbooth.public.v1.yaml" in html
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()
