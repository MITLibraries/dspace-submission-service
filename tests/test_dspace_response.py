from unittest.mock import MagicMock, PropertyMock

import pytest
import requests

from submitter.dspace_response import (
    MAX_BODY_BYTES,
    TRUNCATION_SUFFIX,
    DSpaceResponseLabel,
    capture_responses,
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
