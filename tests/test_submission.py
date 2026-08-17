# ruff: noqa: SLF001
import re
import sys
import traceback
from unittest.mock import MagicMock, patch

import pytest
from dspace_rest_client.client import DSpaceClient
from dspace_rest_client.models import Bitstream, Bundle, Item
from freezegun import freeze_time
from requests.exceptions import RequestException

from submitter import errors
from submitter.submission import Submission, dspace_clients, prettify


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
    with pytest.raises(errors.InvalidDSpaceDestinationError):
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
    assert "Error creating bundle:" in caplog.text


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
    assert "Error creating bitstream:" in caplog.text


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
