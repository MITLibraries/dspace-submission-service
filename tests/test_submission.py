# ruff: noqa: SLF001
import re
import sys
import traceback
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests
import requests_mock
from dspace_rest_client.client import DSpaceClient
from dspace_rest_client.models import Bitstream, Bundle, Item
from freezegun import freeze_time
from requests.exceptions import RequestException

from submitter import errors
from submitter.submission import (
    DSPACE_RESPONSE_LOG_MAX_CHARS,
    Submission,
    dspace_clients,
    log_dspace_response,
    prettify,
    track_last_response,
)


def test_dspace_client_cache_stores_by_destination(
    mocked_dspace, input_message_good_ddc8, input_message_good_dspace_mit
):
    assert dspace_clients == {}
    submission_ddc8 = Submission.from_message(input_message_good_ddc8)
    submission_ddc8.submit()
    assert dspace_clients == {"DDC-8": submission_ddc8.client}
    submission_dspace_mit = Submission.from_message(input_message_good_dspace_mit)
    submission_dspace_mit.submit()
    assert dspace_clients == {
        "DDC-8": submission_ddc8.client,
        "DSpace@MIT": submission_dspace_mit.client,
    }


def test_submission_get_dspace_client_success(mocked_dspace):
    submission = Submission(
        destination="IR-8",
        attributes=None,
        result_queue=None,
    )
    dspace_client = submission.get_dspace_client()
    assert isinstance(dspace_client, DSpaceClient)


def test_submission_get_dspace_client_no_auth_raises_error(
    mocked_dspace_auth_failure,
):
    submission = Submission(
        destination="IR-8",
        attributes=None,
        result_queue=None,
    )
    with pytest.raises(errors.DSpaceAuthenticationError):
        submission.get_dspace_client()


def test_submission_get_dspace_client_invalid_destination_raises_error():
    submission = Submission(
        destination="InvalidDestination",
        attributes=None,
        result_queue=None,
    )
    with pytest.raises(
        ValueError,
        match=re.escape(
            "'submission_system' should be one of ['DSpace@MIT','IR-8', 'DDC-8'], got 'InvalidDestination'"  # noqa: E501
        ),
    ):
        submission.get_dspace_client()


def test_submission_get_dspace_client_no_destination_raises_error():
    submission = Submission(
        destination=None,
        attributes=None,
        result_queue=None,
    )
    with pytest.raises(errors.InvalidDSpaceDestinationError):
        submission.get_dspace_client()


def test_submission_from_message_success(input_message_good_dspace_mit, mocked_dspace):
    submission = Submission.from_message(input_message_good_dspace_mit)
    assert submission.destination == "DSpace@MIT"
    assert submission.collection_handle == "0000/collection01"
    assert submission.metadata_location == "tests/fixtures/test-item-metadata.json"
    assert submission.files == [
        {
            "BitstreamName": "test-file-01.pdf",
            "FileLocation": "tests/fixtures/test-file-01.pdf",
            "BitstreamDescription": "A test bitstream",
        }
    ]
    assert submission.result_attributes == {
        "PackageID": {"DataType": "String", "StringValue": "etdtest01"},
        "SubmissionSource": {"DataType": "String", "StringValue": "etd"},
    }
    assert submission.result_message is None
    assert submission.result_queue == "empty_result_queue"


def test_submission_from_message_defaults_to_create_operation(
    input_message_good_dspace_mit,
):
    submission = Submission.from_message(input_message_good_dspace_mit)

    assert "Operation" not in input_message_good_dspace_mit.body
    assert submission.operation == "create"


def test_submission_from_message_body_jsondecodeerror_handled(
    input_message_invalid_json, mocked_dspace
):
    submission = Submission.from_message(input_message_invalid_json)
    assert submission.result_message == (
        "Unable to parse submission message body. Message body provided was: "
        "'Doesn't conform to the DSS spec'"
    )


def test_submission_from_message_body_missing_required_property_is_handled(
    input_message_missing_collection_handle,
):
    submission = Submission.from_message(input_message_missing_collection_handle)
    assert "'CollectionHandle' is a required property" in submission.result_message


def test_submission_from_message_attr_invalid_queue_raises_validationerror(
    input_message_invalid_queue, mocked_dspace
):
    with pytest.raises(
        errors.SubmissionMessageAttributesValidationError,
        match=re.escape("'not-a-queue' is not one of ['empty_result_queue']"),
    ):
        Submission.from_message(input_message_invalid_queue)


def test_submission_from_message_attr_missing_required_property_raises_validationerror(
    input_message_missing_attribute,
):
    with pytest.raises(
        errors.SubmissionMessageAttributesValidationError,
        match=re.escape("'SubmissionSource' is a required property"),
    ):
        Submission.from_message(input_message_missing_attribute)


@freeze_time("2021-09-01 05:06:07")
def test_result_error_message(input_message_item_create_error, mocked_dspace):
    submission = Submission.from_message(input_message_item_create_error)
    submission.result_error_message(
        "A test error", dspace_response="A test DSpace response"
    )
    assert submission.result_message["ResultType"] == "error"
    assert submission.result_message["ErrorTimestamp"] == "2021-09-01 05:06:07"
    assert submission.result_message["ErrorInfo"] == "A test error"
    assert submission.result_message["DSpaceResponse"] == "A test DSpace response"
    assert submission.result_message["ExceptionTraceback"] == prettify(
        traceback.format_exception(*sys.exc_info())
    )


@patch("submitter.submission.DSpaceClient.get_bitstreams")
def test_result_success_message(mock_get_bitstreams, dspace_submission_instance):
    bitstream = Bitstream(
        {
            "uuid": "1234-5678-9000",
            "name": "A test bitstream",
            "checkSum": "a4e0f4930dfaff904fa3c6c85b0b8ecc",
            "checkSumAlgorithm": "MD5",
        }
    )
    mock_get_bitstreams.return_value = [bitstream]

    item = Item(
        {
            "handle": "0000/12345",
            "lastModified": "yesterday",
        }
    )
    bundle = Bundle({"uuid": "bundle01"})

    dspace_submission_instance.result_success_message(item, bundle)
    assert dspace_submission_instance.result_message["ResultType"] == "success"
    assert dspace_submission_instance.result_message["ItemHandle"] == item.handle
    assert dspace_submission_instance.result_message["lastModified"] == item.lastModified
    assert dspace_submission_instance.result_message["Bitstreams"] == [
        {
            "BitstreamName": bitstream.name,
            "BitstreamUUID": bitstream.uuid,
            "BitstreamChecksum": bitstream.checkSum,
        }
    ]


@patch("submitter.submission.DSpaceClient.get_bitstreams")
def test_submit_success(mock_get_bitstreams, dspace_submission_instance):
    mock_get_bitstreams.return_value = [
        Bitstream({"uuid": "bitstream01", "bundleName": "bundle01"})
    ]
    dspace_submission_instance.submit()
    assert dspace_submission_instance.result_message["ResultType"] == "success"


def test_submit_item_success(dspace_submission_instance):
    item, bundle = dspace_submission_instance._submit_item()
    assert item.uuid == "item01"
    assert bundle.uuid == "bundle01"


@patch("submitter.submission.DSpaceClient.create_item")
def test_submit_item_error(mock_create_item, dspace_submission_instance):
    mock_create_item.return_value = Item()
    with pytest.raises(errors.ItemError):
        dspace_submission_instance._submit_item()


@patch("submitter.submission.DSpaceClient.create_bundle")
def test_submit_item_bundle_create_error_raises_exception(
    mock_create_bundle, dspace_submission_instance, caplog
):
    mock_create_bundle.side_effect = RequestException
    with pytest.raises(errors.BundleError):
        dspace_submission_instance._submit_item()


@patch("submitter.submission.DSpaceClient.create_bitstream")
def test_submit_item_bitstream_error_raises_exception(
    mock_create_bitstream,
    mocked_dspace,
    dspace_submission_instance,
    caplog,
):
    mock_create_bitstream.side_effect = RequestException

    with pytest.raises(errors.BitstreamError):
        dspace_submission_instance._submit_item()


@patch("submitter.submission.DSpaceClient.create_bitstream")
def test_submit_item_bitstream_error_triggers_cleanup(
    mock_create_bitstream, mocked_dspace, dspace_submission_instance, caplog
):
    bitstream = Bitstream({"uuid": "bitstream01", "bundleName": "bundle01"})
    mock_create_bitstream.side_effect = [bitstream, RequestException]

    with pytest.raises(errors.BitstreamError):
        dspace_submission_instance._submit_item()

    assert "Item '0000/item01' was partially posted to DSpace, cleaning up" in caplog.text
    assert "Item '0000/item01' deleted from DSpace" in caplog.text


@patch("submitter.submission.DSpaceClient.delete_dso")
@patch("submitter.submission.DSpaceClient.create_bitstream")
def test_submit_item_bitstream_error_cleanup_failure_logs_exception(
    mock_create_bitstream, mock_delete_dso, dspace_submission_instance, caplog
):
    bitstream = Bitstream({"uuid": "bitstream01", "bundleName": "bundle01"})
    mock_create_bitstream.side_effect = [bitstream, RequestException]
    mock_delete_dso.side_effect = RequestException

    with pytest.raises(errors.BitstreamError):
        dspace_submission_instance._submit_item()

    assert "Item '0000/item01' was partially posted to DSpace, cleaning up" in caplog.text
    assert "Failed to delete DSpace item '0000/item01'" in caplog.text


@patch("submitter.submission.Submission._delete_old_item_bitstream")
@patch("submitter.submission.Submission._upload_new_item_bitstreams")
@patch("submitter.submission.Submission._get_item_bitstream_bundle")
def test_update_item_bitstream_with_old_bitstream_success(
    mock_get_item_bitstream_bundle,
    mock_upload_new_item_bitstreams,
    mock_delete_old_item_bitstream,
    dspace_submission_instance,
):
    item = MagicMock()
    mock_get_item_bitstream_bundle.return_value = (
        MagicMock(name="old-test-file-01.pdf"),  # the old bitstream
        MagicMock(),  # the bundle
    )
    mock_upload_new_item_bitstreams.return_value[
        MagicMock(name="test-file-01.pdf"), MagicMock(name="test-file-02.pdf")
    ]
    dspace_submission_instance._update_item_bitstream(item)

    mock_delete_old_item_bitstream.assert_called_once()


@patch("submitter.submission.Submission._delete_old_item_bitstream")
@patch("submitter.submission.Submission._upload_new_item_bitstreams")
@patch("submitter.submission.Submission._get_item_bitstream_bundle")
def test_update_item_bitstream_without_old_bitstream_success(
    mock_get_item_bitstream_bundle,
    mock_upload_new_item_bitstreams,
    mock_delete_old_item_bitstream,
    dspace_submission_instance,
):
    item = MagicMock()
    mock_get_item_bitstream_bundle.return_value = (
        None,  # the old bitstream
        MagicMock(),  # the bundle
    )
    mock_upload_new_item_bitstreams.return_value[
        MagicMock(name="test-file-01.pdf"), MagicMock(name="test-file-02.pdf")
    ]
    dspace_submission_instance._update_item_bitstream(item)

    mock_delete_old_item_bitstream.assert_not_called()


@patch("submitter.submission.DSpaceClient.create_bitstream")
@patch("submitter.submission.Submission._delete_old_item_bitstream")
@patch("submitter.submission.Submission._undo_bitstream_updates")
@patch("submitter.submission.Submission._get_item_bitstream_bundle")
def test_update_item_bitstream_undo_not_required_raise_error(
    mock_get_item_bitstream_bundle,
    mock_undo_bitstream_updates,
    mock_delete_old_item_bitstream,
    mock_dspace_client_create_bitstream,
    dspace_submission_instance,
):
    item = MagicMock()
    mock_get_item_bitstream_bundle.return_value = (
        MagicMock(name="old-test-file-01.pdf"),  # the old bitstream
        MagicMock(),  # the bundle
    )
    mock_dspace_client_create_bitstream.side_effect = [
        Exception("Failed to create bitstream"),  # first bitstream failed
        Exception("Failed to create bitstream"),  # second bitstream failed
    ]

    with pytest.raises(
        errors.BitstreamError,
    ) as exception:
        dspace_submission_instance._update_item_bitstream(item)

    mock_undo_bitstream_updates.assert_not_called()
    mock_delete_old_item_bitstream.assert_not_called()
    assert "restored item to original state" not in str(exception)


@patch("submitter.submission.DSpaceClient.create_bitstream")
@patch("submitter.submission.Submission._delete_old_item_bitstream")
@patch("submitter.submission.Submission._undo_bitstream_updates")
@patch("submitter.submission.Submission._get_item_bitstream_bundle")
def test_update_item_bitstream_undo_restores_item_state_raise_error(
    mock_get_item_bitstream_bundle,
    mock_undo_bitstream_updates,
    mock_delete_old_item_bitstream,
    mock_dspace_client_create_bitstream,
    dspace_submission_instance,
):
    item = MagicMock()
    mock_get_item_bitstream_bundle.return_value = (
        MagicMock(name="old-test-file-01.pdf"),  # the old bitstream
        MagicMock(),  # the bundle
    )
    mock_dspace_client_create_bitstream.side_effect = [
        MagicMock(name="test-file-01.pdf"),  # first bitstream was successful
        Exception("Failed to create bitstream"),  # second bitstream failed
    ]
    mock_undo_bitstream_updates.return_value = []  # undo creation of first new bitstream

    with pytest.raises(
        errors.BitstreamError,
        match=r"restored item to original state",
    ):
        dspace_submission_instance._update_item_bitstream(item)

    mock_undo_bitstream_updates.assert_called_once()
    mock_delete_old_item_bitstream.assert_not_called()


@patch("submitter.submission.DSpaceClient.create_bitstream")
@patch("submitter.submission.Submission._delete_old_item_bitstream")
@patch("submitter.submission.Submission._undo_bitstream_updates")
@patch("submitter.submission.Submission._get_item_bitstream_bundle")
def test_update_item_bitstream_undo_fails_to_restore_item_state_raise_error(
    mock_get_item_bitstream_bundle,
    mock_undo_bitstream_updates,
    mock_delete_old_item_bitstream,
    mock_dspace_client_create_bitstream,
    dspace_submission_instance,
):
    item = MagicMock()
    mock_get_item_bitstream_bundle.return_value = (
        MagicMock(name="old-test-file-01.pdf"),  # the old bitstream
        MagicMock(),  # the bundle
    )
    mock_dspace_client_create_bitstream.side_effect = [
        MagicMock(name="test-file-01.pdf"),  # first bitstream was successful
        Exception("Failed to create bitstream"),  # second bitstream failed
    ]
    mock_undo_bitstream_updates.return_value = ["test-file-02.pdf"]

    with pytest.raises(
        errors.BitstreamError,
        match=re.escape(
            "Please delete the following bitstreams to restore item state: ['test-file-02.pdf']"  # noqa: E501
        ),
    ):
        dspace_submission_instance._update_item_bitstream(item)

    mock_undo_bitstream_updates.assert_called_once()
    mock_delete_old_item_bitstream.assert_not_called()


@patch("submitter.submission.DSpaceClient.delete_dso")
def test_clean_up_partial_success_non_204_delete_logs_error(
    mock_delete_dso, dspace_submission_instance, caplog
):
    # delete_dso returns None (no exception) when DSpace responds with non-204
    mock_delete_dso.return_value = None
    item = Item({"handle": "0000/item01", "uuid": "item01"})

    with caplog.at_level("INFO"):
        dspace_submission_instance.clean_up_partial_success(item)

    assert "could not be deleted and may remain in DSpace" in caplog.text
    assert "deleted from DSpace" not in caplog.text


@patch("submitter.submission.DSpaceClient.delete_dso")
def test_clean_up_partial_success_204_delete_logs_success(
    mock_delete_dso, dspace_submission_instance, caplog
):
    mock_delete_dso.return_value = requests.Response()
    item = Item({"handle": "0000/item01", "uuid": "item01"})

    with caplog.at_level("INFO"):
        dspace_submission_instance.clean_up_partial_success(item)

    assert "Item '0000/item01' deleted from DSpace" in caplog.text
    assert "Failed to delete" not in caplog.text


def test_log_dspace_response_logs_body(caplog):
    with caplog.at_level("ERROR"):
        log_dspace_response("line one\n  line two")
    assert "DSpace response body: line one line two" in caplog.text


def test_log_dspace_response_truncates_long_body(caplog):
    with caplog.at_level("ERROR"):
        log_dspace_response("x" * (DSPACE_RESPONSE_LOG_MAX_CHARS + 500))
    assert "x" * DSPACE_RESPONSE_LOG_MAX_CHARS + "... [truncated]" in caplog.text
    assert "x" * (DSPACE_RESPONSE_LOG_MAX_CHARS + 1) not in caplog.text


def test_log_dspace_response_no_body_logs_nothing(caplog):
    with caplog.at_level("ERROR"):
        log_dspace_response(None)
    assert "DSpace response body" not in caplog.text


@patch("submitter.submission.DSpaceClient.create_bundle")
def test_submit_item_error_logs_dspace_response_body(
    mock_create_bundle, dspace_submission_instance, caplog
):
    response = requests.Response()
    response.status_code = 500
    response._content = b"DSpace internal failure details"
    mock_create_bundle.side_effect = requests.HTTPError(response=response)
    with caplog.at_level("ERROR"), pytest.raises(errors.BundleError):
        dspace_submission_instance._submit_item()
    assert "DSpace response body: DSpace internal failure details" in caplog.text


def test_track_last_response_records_latest_response():
    client = SimpleNamespace(session=requests.Session())
    track_last_response(client)
    with requests_mock.Mocker() as m:
        m.get("mock://dspace.edu/ok", status_code=200, text="fine")
        m.get("mock://dspace.edu/fail", status_code=500, text="broken")
        client.session.get("mock://dspace.edu/ok")
        assert client.last_response.status_code == HTTPStatus.OK
        client.session.get("mock://dspace.edu/fail")
        assert client.last_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert client.last_response.text == "broken"


def test_failed_dspace_response_returns_none_for_success(dspace_submission_instance):
    response = requests.Response()
    response.status_code = 201
    dspace_submission_instance.client.last_response = response
    assert dspace_submission_instance._failed_dspace_response() is None


def test_failed_dspace_response_returns_body_for_error(dspace_submission_instance):
    response = requests.Response()
    response.status_code = 500
    response._content = b"server exploded"
    dspace_submission_instance.client.last_response = response
    assert dspace_submission_instance._failed_dspace_response() == "server exploded"


def test_create_item_error_includes_dspace_response(
    mocked_dspace, dspace_submission_instance, caplog
):
    track_last_response(dspace_submission_instance.client)
    mocked_dspace.post(
        "mock://dspace.edu/server/api/core/items",
        status_code=500,
        text="item creation failed",
    )
    with caplog.at_level("ERROR"), pytest.raises(errors.ItemError) as exc_info:
        dspace_submission_instance._submit_item()
    assert exc_info.value.dspace_error == "item creation failed"
    assert "DSpace response body: item creation failed" in caplog.text


def test_create_bundle_error_includes_dspace_response(
    mocked_dspace, dspace_submission_instance, caplog
):
    track_last_response(dspace_submission_instance.client)
    mocked_dspace.post(
        "mock://dspace.edu/server/api/core/items/item01/bundles",
        status_code=500,
        text="bundle creation failed",
    )
    with caplog.at_level("ERROR"), pytest.raises(errors.BundleError) as exc_info:
        dspace_submission_instance._submit_item()
    assert exc_info.value.dspace_error == "bundle creation failed"
    assert "DSpace response body: bundle creation failed" in caplog.text


@patch("submitter.submission.DSpaceClient.create_bitstream")
def test_create_bitstream_error_includes_dspace_response(
    mock_create_bitstream, mocked_dspace, dspace_submission_instance, caplog
):
    def failing_create_bitstream(*_args, **_kwargs):
        response = requests.Response()
        response.status_code = 500
        response._content = b"bitstream upload failed"
        dspace_submission_instance.client.last_response = response

    mock_create_bitstream.side_effect = failing_create_bitstream
    with caplog.at_level("ERROR"), pytest.raises(errors.BitstreamError) as exc_info:
        dspace_submission_instance._submit_item()
    assert exc_info.value.dspace_error == "bitstream upload failed"
    assert "DSpace response body: bitstream upload failed" in caplog.text


def test_reset_last_response_clears_stale_failure(dspace_submission_instance):
    response = requests.Response()
    response.status_code = 500
    response._content = b"stale failure"
    dspace_submission_instance.client.last_response = response
    dspace_submission_instance._reset_last_response()
    assert dspace_submission_instance._failed_dspace_response() is None


def test_upload_new_item_bitstreams_failure_includes_dspace_response(
    mocked_dspace, dspace_submission_instance
):
    track_last_response(dspace_submission_instance.client)
    mocked_dspace.post(
        "mock://dspace.edu/server/api/core/bundles/bundle01/bitstreams",
        status_code=500,
        text="bitstream upload rejected",
    )
    bundle = Bundle(api_resource={"uuid": "bundle01", "name": "ORIGINAL"})
    item = Item({"handle": "0000/item01", "uuid": "item01"})
    with pytest.raises(errors.BitstreamError) as exc_info:
        dspace_submission_instance._upload_new_item_bitstreams(item, bundle)
    assert exc_info.value.dspace_error == "bitstream upload rejected"


def test_upload_new_item_bitstreams_undo_failure_keeps_dspace_response(
    dspace_submission_instance,
):
    bitstream = SimpleNamespace(name="test-file-01.pdf")
    dspace_submission_instance.files = [
        {
            "BitstreamName": "test-file-01.pdf",
            "FileLocation": "tests/fixtures/test-file-01.pdf",
        },
        {
            "BitstreamName": "test-file-02.pdf",
            "FileLocation": "tests/fixtures/test-file-01.pdf",
        },
    ]
    response = requests.Response()
    response.status_code = 500
    response._content = b"second upload failed"

    def create_bitstream(**kwargs):
        if kwargs["name"] == "test-file-01.pdf":
            return bitstream
        dspace_submission_instance.client.last_response = response
        return None

    bundle = Bundle(api_resource={"uuid": "bundle01", "name": "ORIGINAL"})
    item = Item({"handle": "0000/item01", "uuid": "item01"})
    with (
        patch.object(
            dspace_submission_instance.client,
            "create_bitstream",
            side_effect=create_bitstream,
        ),
        patch.object(
            dspace_submission_instance,
            "_undo_bitstream_updates",
            return_value=[],
        ),
        pytest.raises(errors.BitstreamError) as exc_info,
    ):
        dspace_submission_instance._upload_new_item_bitstreams(item, bundle)
    assert exc_info.value.dspace_error == "second upload failed"


@patch("submitter.submission.DSpaceClient.api_delete")
def test_delete_bitstream_non_204_includes_dspace_response(
    mock_api_delete, dspace_submission_instance
):
    response = requests.Response()
    response.status_code = 500
    response._content = b"delete refused"
    mock_api_delete.return_value = response
    bitstream = SimpleNamespace(
        links={"self": {"href": "mock://dspace.edu/bitstreams/bs01"}},
        uuid="bs01",
        name="test-file-01.pdf",
    )
    with pytest.raises(errors.BitstreamError) as exc_info:
        dspace_submission_instance._delete_bitstream(bitstream)
    assert exc_info.value.dspace_error == "delete refused"


@patch("submitter.submission.Submission._delete_bitstream")
def test_delete_old_item_bitstream_preserves_dspace_response(
    mock_delete_bitstream, dspace_submission_instance
):
    mock_delete_bitstream.side_effect = errors.BitstreamError(
        "delete failed", dspace_response="original delete body"
    )
    item = Item({"handle": "0000/item01", "uuid": "item01"})
    bitstream = SimpleNamespace(name="old.pdf", uuid="bs01")
    with pytest.raises(errors.BitstreamError) as exc_info:
        dspace_submission_instance._delete_old_item_bitstream(item, bitstream)
    assert exc_info.value.dspace_error == "original delete body"


@patch("submitter.submission.Submission._delete_bitstream")
def test_undo_bitstream_updates_logs_dspace_response(
    mock_delete_bitstream, dspace_submission_instance, caplog
):
    mock_delete_bitstream.side_effect = errors.BitstreamError(
        "delete failed", dspace_response="undo delete body"
    )
    bitstream = Bitstream(api_resource={"uuid": "bs02", "name": "new.pdf"})
    with caplog.at_level("ERROR"):
        remaining = dspace_submission_instance._undo_bitstream_updates([bitstream])
    assert remaining == [bitstream]
    assert "DSpace response body: undo delete body" in caplog.text


def test_clean_up_partial_success_non_204_logs_dspace_response(
    mocked_dspace, dspace_submission_instance, caplog
):
    track_last_response(dspace_submission_instance.client)
    mocked_dspace.delete(
        "mock://dspace.edu/server/api/core/items/item01",
        status_code=500,
        text="item delete rejected",
    )
    item = Item(
        {
            "handle": "0000/item01",
            "uuid": "item01",
            "_links": {
                "self": {"href": "mock://dspace.edu/server/api/core/items/item01"}
            },
        }
    )
    with caplog.at_level("ERROR"):
        dspace_submission_instance.clean_up_partial_success(item)
    assert "may remain in DSpace" in caplog.text
    assert "DSpace response body: item delete rejected" in caplog.text


def test_clean_up_partial_success_exception_does_not_log_stale_body(
    dspace_submission_instance, caplog
):
    stale = requests.Response()
    stale.status_code = 500
    stale._content = b"stale body"
    dspace_submission_instance.client.last_response = stale
    item = Item({"handle": "0000/item01", "uuid": "item01"})
    with (
        patch(
            "submitter.submission.DSpaceClient.delete_dso",
            side_effect=RequestException("connection dropped"),
        ),
        caplog.at_level("ERROR"),
    ):
        dspace_submission_instance.clean_up_partial_success(item)
    assert "may remain in DSpace" in caplog.text
    assert "stale body" not in caplog.text


def test_add_provenance_entry_raises_with_dspace_response_on_failure(
    mocked_dspace, dspace_submission_instance
):
    track_last_response(dspace_submission_instance.client)
    mocked_dspace.patch(
        "mock://dspace.edu/server/api/core/items/item01",
        status_code=500,
        text="provenance rejected",
    )
    item = Item(
        {
            "handle": "0000/item01",
            "uuid": "item01",
            "_links": {
                "self": {"href": "mock://dspace.edu/server/api/core/items/item01"}
            },
        }
    )
    with pytest.raises(errors.ItemError) as exc_info:
        dspace_submission_instance._add_provenance_entry(item, "Deleted bitstream")
    assert "Error occurred while adding provenance entry to item '0000/item01'" in str(
        exc_info.value
    )
    assert exc_info.value.dspace_error == "provenance rejected"


@patch("submitter.submission.Submission._delete_old_item_bitstream")
@patch("submitter.submission.Submission._upload_new_item_bitstreams")
@patch("submitter.submission.Submission._get_item_bitstream_bundle")
@patch("submitter.submission.DSpaceClient.add_metadata")
def test_update_item_bitstream_provenance_failure_stops_update(
    mock_add_metadata,
    mock_get_bundle,
    mock_upload,
    mock_delete_old,
    dspace_submission_instance,
):
    old_bitstream = SimpleNamespace(name="old.pdf")
    bundle = Bundle(api_resource={"uuid": "bundle01", "name": "ORIGINAL"})
    mock_get_bundle.return_value = (old_bitstream, bundle)
    mock_upload.return_value = [SimpleNamespace(name="new.pdf")]
    mock_add_metadata.side_effect = lambda *_args, **_kwargs: None
    item = Item({"handle": "0000/item01", "uuid": "item01"})
    with (
        patch.object(
            dspace_submission_instance,
            "_failed_dspace_response",
            return_value="provenance rejected",
        ),
        pytest.raises(errors.ItemError),
    ):
        dspace_submission_instance._update_item_bitstream(item)
    mock_delete_old.assert_not_called()


def test_add_provenance_entry_success_logs_nothing(
    mocked_dspace, dspace_submission_instance, caplog
):
    track_last_response(dspace_submission_instance.client)
    mocked_dspace.patch(
        "mock://dspace.edu/server/api/core/items/item01",
        status_code=200,
        json={"type": "item", "id": "item01", "handle": "0000/item01"},
    )
    item = Item(
        {
            "handle": "0000/item01",
            "uuid": "item01",
            "_links": {
                "self": {"href": "mock://dspace.edu/server/api/core/items/item01"}
            },
        }
    )
    with caplog.at_level("ERROR"):
        dspace_submission_instance._add_provenance_entry(item, "Deleted bitstream")
    assert "DSpace response body" not in caplog.text


@patch("submitter.submission.DSpaceClient.create_bundle")
def test_create_bundle_exception_includes_dspace_response(
    mock_create_bundle, dspace_submission_instance, mocked_dspace
):
    track_last_response(dspace_submission_instance.client)

    def failing_create_bundle(**_kwargs):
        # Simulate a failed request, then an exception raised without a response body
        dspace_submission_instance.client.session.post(
            "mock://dspace.edu/server/api/core/items/item01/bundles"
        )
        raise RuntimeError("connection reset")

    mocked_dspace.post(
        "mock://dspace.edu/server/api/core/items/item01/bundles",
        status_code=500,
        text="bundle creation rejected",
    )
    mock_create_bundle.side_effect = failing_create_bundle
    mocked_dspace.delete(
        "mock://dspace.edu/server/api/core/items/item01", status_code=204
    )
    item = Item({"handle": "0000/item01", "uuid": "item01"})
    with pytest.raises(errors.BundleError) as exc_info:
        dspace_submission_instance._create_bundle(item)
    assert exc_info.value.dspace_error == "bundle creation rejected"


@patch("submitter.submission.DSpaceClient.create_bitstream")
def test_create_bitstream_exception_includes_dspace_response(
    mock_create_bitstream, dspace_submission_instance, mocked_dspace
):
    track_last_response(dspace_submission_instance.client)

    def failing_create_bitstream(**_kwargs):
        # Simulate a failed request, then an exception raised without a response body
        dspace_submission_instance.client.session.post(
            "mock://dspace.edu/server/api/core/bundles/bundle01/bitstreams"
        )
        raise RuntimeError("connection reset")

    mocked_dspace.post(
        "mock://dspace.edu/server/api/core/bundles/bundle01/bitstreams",
        status_code=500,
        text="bitstream creation rejected",
    )
    mock_create_bitstream.side_effect = failing_create_bitstream
    mocked_dspace.delete(
        "mock://dspace.edu/server/api/core/items/item01", status_code=204
    )
    bundle = Bundle(api_resource={"uuid": "bundle01", "name": "ORIGINAL"})
    item = Item({"handle": "0000/item01", "uuid": "item01"})
    with pytest.raises(errors.BitstreamError) as exc_info:
        dspace_submission_instance._create_bitstream(
            item,
            bundle,
            {
                "BitstreamName": "test-file-01.pdf",
                "FileLocation": "tests/fixtures/test-file-01.pdf",
            },
        )
    assert exc_info.value.dspace_error == "bitstream creation rejected"
