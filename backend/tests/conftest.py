from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND.parent) not in sys.path:
    sys.path.insert(0, str(BACKEND.parent))

import pytest
from backend.app.config import settings

_language_results: dict[tuple[str, str], list[str]] = {}

def pytest_collection_modifyitems(items):
    if settings.use_mock_voice or not settings.gnani_api_key:
        skip_live = pytest.mark.skip(reason="live provider tests require USE_MOCK_VOICE=false and a locally configured Gnani key")
        for item in items:
            if item.get_closest_marker("live"):
                item.add_marker(skip_live)

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not hasattr(item, "callspec"):
        return
    case = item.callspec.params.get("case")
    if not isinstance(case, dict):
        return
    key = (case["language"], case.get("scenario", case["id"]))
    _language_results.setdefault(key, []).append("FAIL" if report.failed else "PASS")

def pytest_terminal_summary(terminalreporter):
    if not _language_results:
        return
    terminalreporter.write_sep("=", "Language scenario summary (offline text/API cases)")
    terminalreporter.write_line("| Language | Scenario | Result |")
    terminalreporter.write_line("|---|---|---|")
    for (language, scenario), outcomes in sorted(_language_results.items()):
        status = "FAIL" if "FAIL" in outcomes else "PASS"
        terminalreporter.write_line(f"| {language} | {scenario} | {status} |")

