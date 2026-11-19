from unittest.mock import MagicMock, PropertyMock

import pytest
import requests

from submitter.dspace_response import (
    MAX_BODY_BYTES,
    TRUNCATION_SUFFIX,
    DSpaceResponseLabel,
    capture_responses,
    format_response,
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


def test_format_response_renders_entry():
    entry = {
        "status_code": 500,
        "url": "mock://dspace.edu/x",
        "method": "POST",
        "elapsed": 0.5,
        "body": "oops",
    }
    assert format_response(entry) == "POST mock://dspace.edu/x -> 500 (0.5s): oops"


def test_format_response_handles_missing_fields():
    assert "None" in format_response({})


def test_capture_responses_yields_only_entries_from_this_context(mocked_dspace):
    session = requests.Session()
    collector = {}
    with capture_responses(session, collector, DSpaceResponseLabel.CREATE_ITEM) as first:
        session.get("mock://dspace.edu/server/api/pid/find")
    with capture_responses(session, collector, DSpaceResponseLabel.CREATE_ITEM) as second:
        session.get("mock://dspace.edu/server/api/pid/find")
    assert len(first) == len(second) == 1
    assert len(collector["create_item"]) == 2  # noqa: PLR2004
