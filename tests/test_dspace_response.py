import logging
from unittest.mock import MagicMock, PropertyMock

import pytest
import requests

from submitter.dspace_response import (
    MAX_BODY_BYTES,
    TRUNCATION_SUFFIX,
    DSpaceResponseLabel,
    capture_responses,
    log_failed_responses,
    truncate_body,
)


def test_truncate_body_short_unchanged():
    assert truncate_body("hello") == "hello"


def test_truncate_body_long_truncated_with_suffix():
    result = truncate_body("a" * (MAX_BODY_BYTES + 100))
    assert result == "a" * MAX_BODY_BYTES + TRUNCATION_SUFFIX


def test_capture_responses_records_and_detaches_hook(mocked_dspace):
    session = requests.Session()
    collector: dict = {}
    with capture_responses(session, collector, DSpaceResponseLabel.CREATE_ITEM):
        session.get("mock://dspace.edu/server/api/pid/find")
    session.get("mock://dspace.edu/server/api/pid/find")
    assert session.hooks["response"] == []
    assert len(collector["create_item"]) == 1
    assert set(collector["create_item"][0]) == {
        "status_code",
        "url",
        "method",
        "elapsed",
        "body",
    }
    assert isinstance(collector["create_item"][0]["elapsed"], float)


def test_capture_responses_skips_auth_urls(mocked_dspace):
    session = requests.Session()
    collector: dict = {}
    with capture_responses(session, collector, DSpaceResponseLabel.CREATE_ITEM):
        session.get("mock://dspace.edu/server/api/authn/status")
    assert collector == {}


def test_capture_responses_hook_failure_does_not_propagate():
    session = requests.Session()
    collector: dict = {}
    response = MagicMock(url="mock://x/api/core/items")
    type(response).text = PropertyMock(side_effect=RuntimeError("boom"))
    response.status_code = 500
    response.elapsed = None
    with capture_responses(session, collector, DSpaceResponseLabel.CREATE_ITEM):
        for hook in session.hooks["response"]:
            hook(response)
    assert collector["create_item"][0]["body"] == "<unreadable>"


def test_capture_responses_detaches_hook_on_exception():
    session = requests.Session()
    with (
        pytest.raises(ValueError, match="boom"),
        capture_responses(session, {}, DSpaceResponseLabel.CREATE_ITEM),
    ):
        raise ValueError("boom")
    assert session.hooks["response"] == []


def _logged(caplog):
    return [r for r in caplog.records if r.name == "submitter.dspace_response"]


def test_log_failed_responses_logs_error_with_details(mocked_dspace, caplog):
    mocked_dspace.get(
        "mock://dspace.edu/server/api/core/items/x",
        status_code=500,
        text="boom",
        headers={"Retry-After": "30"},
    )
    session = requests.Session()
    with log_failed_responses(session, "PackageID=pkg1"):
        session.get("mock://dspace.edu/server/api/core/items/x")
    records = _logged(caplog)
    assert len(records) == 1
    assert records[0].levelno == logging.ERROR
    message = records[0].getMessage()
    for expected in ("PackageID=pkg1", "GET", "/core/items/x", "500", "boom", "30"):
        assert expected in message


@pytest.mark.parametrize("status_code", [200, 201, 204, 302])
def test_log_failed_responses_ignores_non_failures(mocked_dspace, caplog, status_code):
    mocked_dspace.get("mock://dspace.edu/server/api/ok", status_code=status_code)
    session = requests.Session()
    with log_failed_responses(session, "ctx"):
        session.get("mock://dspace.edu/server/api/ok", allow_redirects=False)
    assert _logged(caplog) == []


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 500])
def test_log_failed_responses_logs_all_4xx_and_5xx_as_error(
    mocked_dspace, caplog, status_code
):
    mocked_dspace.get("mock://dspace.edu/server/api/bad", status_code=status_code)
    session = requests.Session()
    with log_failed_responses(session, "ctx"):
        session.get("mock://dspace.edu/server/api/bad")
    records = _logged(caplog)
    assert [r.levelno for r in records] == [logging.ERROR]


def test_log_failed_responses_truncates_body(mocked_dspace, caplog):
    mocked_dspace.get(
        "mock://dspace.edu/server/api/big", status_code=500, text="x" * 20000
    )
    session = requests.Session()
    with log_failed_responses(session, "ctx"):
        session.get("mock://dspace.edu/server/api/big")
    assert TRUNCATION_SUFFIX in _logged(caplog)[0].getMessage()
    assert "x" * (MAX_BODY_BYTES + 1) not in _logged(caplog)[0].getMessage()


def test_log_failed_responses_redacts_sensitive_headers(mocked_dspace, caplog):
    mocked_dspace.get("mock://dspace.edu/server/api/bad", status_code=500)
    session = requests.Session()
    with log_failed_responses(session, "ctx"):
        session.get(
            "mock://dspace.edu/server/api/bad",
            headers={
                "Authorization": "Bearer secret-token",
                "Cookie": "session=secret-cookie",
                "X-XSRF-TOKEN": "secret-csrf",
            },
        )
    message = _logged(caplog)[0].getMessage()
    assert "secret" not in message
    assert "<redacted>" in message


def test_log_failed_responses_skips_authn_requests(mocked_dspace, caplog):
    mocked_dspace.post("mock://dspace.edu/server/api/authn/login", status_code=401)
    session = requests.Session()
    with log_failed_responses(session, "ctx"):
        session.post(
            "mock://dspace.edu/server/api/authn/login",
            data={"user": "me", "password": "hunter2"},
        )
    assert _logged(caplog) == []


def test_log_failed_responses_detaches_hook_on_exception():
    session = requests.Session()
    with (
        pytest.raises(RuntimeError),
        log_failed_responses(session, "ctx"),
    ):
        raise RuntimeError
    assert session.hooks["response"] == []


def test_log_failed_responses_hook_failure_does_not_propagate(mocked_dspace, caplog):
    mocked_dspace.get("mock://dspace.edu/server/api/bad", status_code=500)
    session = requests.Session()
    with log_failed_responses(session, "ctx"):
        hook = session.hooks["response"][0]
        response = MagicMock(status_code=500)
        response.request = None
        type(response).headers = PropertyMock(side_effect=RuntimeError("boom"))
        hook(response)
    assert any("Failed to log DSpace response" in r.getMessage() for r in caplog.records)
