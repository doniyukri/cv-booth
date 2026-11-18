from pathlib import Path

from booth.applications import list_applications, parse_application_log_line


class TestParseApplicationLogLine:
    def test_reads_tab_separated_fields(self) -> None:
        line = "2026-09-24T10:58:45\tPT Sigma Global Teknologi\tFrontend Developer\tfile.pdf"
        assert parse_application_log_line(line) == {
            "when": "2026-09-24T10:58:45",
            "date": "2026-09-24",
            "company": "PT Sigma Global Teknologi",
            "position": "Frontend Developer",
            "pdf": "file.pdf",
        }

    def test_returns_none_for_incomplete_rows(self) -> None:
        assert parse_application_log_line("2026-09-24T10:58:45\tonly-two") is None


class TestListApplications:
    def test_returns_empty_when_log_is_missing(self, tmp_path: Path) -> None:
        assert list_applications(tmp_path / "log.txt") == []

    def test_collapses_same_company_and_position(self, tmp_path: Path) -> None:
        log_path = tmp_path / "log.txt"
        log_path.write_text(
            "2026-09-26T00:05:42\tKeda Tech\tFrontend Engineer\ta.pdf\n"
            "2026-09-26T00:06:49\tKeda Tech\tFrontend Engineer\tb.pdf\n"
            "2026-09-24T10:58:45\tPT Sigma Global Teknologi\tFrontend Developer\tc.pdf\n",
            encoding="utf-8",
        )
        rows = list_applications(log_path)
        assert len(rows) == 2
        assert rows[0].company == "Keda Tech"
        assert rows[0].count == 2
        assert rows[0].pdf == "b.pdf"
        assert rows[1].company == "PT Sigma Global Teknologi"
        assert rows[1].count == 1
