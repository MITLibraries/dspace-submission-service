import sys
import traceback
from unittest.mock import patch

import pytest
from dspace import Bitstream, Item
from dspace.client import DSpaceClient as DSpace6Client
from dspace_rest_client.client import DSpaceClient as DSpace8Client
from freezegun import freeze_time
from requests.exceptions import RequestException

from submitter import errors
from submitter.submission import Submission, prettify


def test_submission_get_dspace_client_dspace6_success(mocked_dspace6):
    submission = Submission(
        destination="DSpace@MIT",
        attributes=None,
        result_queue=None,
    )
    dspace_client = submission.get_dspace_client()
    assert isinstance(dspace_client, DSpace6Client)


def test_submission_get_dspace_client_dspace8_success(mocked_dspace8):
    submission = Submission(
        destination="DSpace8Local",
        attributes=None,
        result_queue=None,
    )
    dspace_client = submission.get_dspace_client()
    assert isinstance(dspace_client, DSpace8Client)


def test_submission_get_dspace_client_dspace8_no_auth_raises_error(
    mocked_dspace8_auth_failure,
):
    submission = Submission(
        destination="DSpace8Local",
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


def test_submission_from_message_dspace6_success(input_message_good, mocked_dspace6):
    submission = Submission.from_message(input_message_good)
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


def test_submission_from_message_dspace6_creates_error_message(
    input_message_nonconforming_body, mocked_dspace6
):
    submission = Submission.from_message(input_message_nonconforming_body)
    assert submission.result_message == (
        "Submission message did not conform to the DSS specification. Message body "
        "provided was: 'Doesn't conform to the DSS spec'"
    )


def test_submission_from_message_dspace6_raises_invalid_queue_error(
    input_message_invalid_queue, mocked_dspace6
):
    with pytest.raises(errors.SubmitMessageInvalidResultQueueError):
        Submission.from_message(input_message_invalid_queue)


def test_submission_from_message_raises_missing_attribute_error(
    input_message_missing_attribute,
):
    with pytest.raises(errors.SubmitMessageMissingAttributeError):
        Submission.from_message(input_message_missing_attribute)


def test_get_metadata_entries_from_file_dspace6(mocked_dspace6):
    submission = Submission(
        destination="DSpace@MIT",
        collection_handle=None,
        metadata_location="tests/fixtures/test-item-metadata.json",
        files=None,
        attributes=None,
        result_queue=None,
    )
    metadata = submission.get_metadata_entries_from_file_dspace6()
    assert next(metadata) == {"key": "dc.title", "value": "Test Thesis"}


@freeze_time("2021-09-01 05:06:07")
def test_result_error_message_dspace6(input_message_good, mocked_dspace6):
    submission = Submission.from_message(input_message_good)
    submission.result_error_message("A test error")
    assert submission.result_message["ResultType"] == "error"
    assert submission.result_message["ErrorTimestamp"] == "2021-09-01 05:06:07"
    assert submission.result_message["ErrorInfo"] == "A test error"
    assert submission.result_message["DSpaceResponse"] == "N/A"
    assert submission.result_message["ExceptionTraceback"] == prettify(
        traceback.format_exception(*sys.exc_info())
    )


def test_result_success_message_dspace6(input_message_good, mocked_dspace6):
    item = Item()
    item.handle = "0000/12345"
    item.lastModified = "yesterday"
    bitstream = Bitstream()
    bitstream.name = "A test bitstream"
    bitstream.uuid = "1234-5678-9000"
    bitstream.checkSum = {
        "value": "a4e0f4930dfaff904fa3c6c85b0b8ecc",
        "checkSumAlgorithm": "MD5",
    }
    item.bitstreams = [bitstream]
    submission = Submission.from_message(input_message_good)
    submission.result_success_message(item)
    assert submission.result_message["ResultType"] == "success"
    assert submission.result_message["ItemHandle"] == item.handle
    assert submission.result_message["lastModified"] == item.lastModified
    assert submission.result_message["Bitstreams"] == [
        {
            "BitstreamName": bitstream.name,
            "BitstreamUUID": bitstream.uuid,
            "BitstreamChecksum": bitstream.checkSum,
        }
    ]


@patch("submitter.submission.DSpace6Client")
def test_submit_dspace6_success(
    mock_dspace_client, test_dspace6_client, mocked_dspace6, input_message_good
):
    mock_dspace_client.return_value = test_dspace6_client
    submission = Submission.from_message(input_message_good)
    submission.submit()
    assert submission.result_message["ResultType"] == "success"


def test_submit_dspace8_success(dspace8_submission_instance):
    dspace8_submission_instance.submit()
    assert dspace8_submission_instance.result_message["ResultType"] == "success"


@patch("submitter.submission.DSpace6Client")
def test_submit_dspace6_item_create_error(
    mock_dspace_client,
    test_dspace6_client,
    mocked_dspace6,
    input_message_item_create_error,
):
    mock_dspace_client.return_value = test_dspace6_client
    submission = Submission.from_message(input_message_item_create_error)
    submission.submit()
    assert submission.result_message["ResultType"] == "error"
    assert (
        submission.result_message["ErrorInfo"]
        == "Error occurred while creating item metadata entries from file "
        "'tests/fixtures/test-item-metadata-error.json'"
    )


@patch("submitter.submission.DSpace6Client")
def test_submit_dspace6_add_bitstreams_error(
    mock_dspace_client,
    test_dspace6_client,
    mocked_dspace6,
    input_message_bitstream_create_error,
):
    mock_dspace_client.return_value = test_dspace6_client
    submission = Submission.from_message(input_message_bitstream_create_error)
    submission.submit()
    assert submission.result_message["ResultType"] == "error"
    assert (
        submission.result_message["ErrorInfo"]
        == "Error occurred while parsing bitstream information from files listed in "
        "submission message."
    )


@patch("submitter.submission.DSpace6Client")
def test_submit_dspace6_item_post_error(
    mock_dspace_client, test_dspace6_client, mocked_dspace6, input_message_item_post_error
):
    mock_dspace_client.return_value = test_dspace6_client
    submission = Submission.from_message(input_message_item_post_error)
    submission.submit()
    assert submission.result_message["ResultType"] == "error"
    assert (
        submission.result_message["ErrorInfo"]
        == "Error occurred while posting item to DSpace collection "
        "'0000/not-a-collection'"
    )


@patch("submitter.submission.DSpace6Client")
def test_submit_dspace6_timeout_raises_error(
    mock_dspace_client,
    test_dspace6_client,
    mocked_dspace6,
    input_message_item_post_dspace_timeout,
):
    mock_dspace_client.return_value = test_dspace6_client
    submission = Submission.from_message(input_message_item_post_dspace_timeout)
    with pytest.raises(errors.DSpaceTimeoutError):
        submission.submit()


@patch("submitter.submission.DSpace6Client")
def test_submit_dspace6_bitstream_post_file_open_error(
    mock_dspace_client,
    test_dspace6_client,
    mocked_dspace6,
    input_message_bitstream_file_open_error,
):
    mock_dspace_client.return_value = test_dspace6_client
    submission = Submission.from_message(input_message_bitstream_file_open_error)
    submission.submit()
    assert submission.result_message["ResultType"] == "error"
    assert submission.result_message["ErrorInfo"] == (
        "Error occurred while opening file 'tests/fixtures/nothing-here' for "
        "bitstream. Item '0000/item01' and any bitstreams already posted to it will "
        "be deleted"
    )


@patch("submitter.submission.DSpace6Client")
def test_submit_dspace6_bitstream_post_dspace_error(
    mock_dspace_client,
    test_dspace6_client,
    mocked_dspace6,
    input_message_bitstream_dspace_post_error,
):
    mock_dspace_client.return_value = test_dspace6_client
    submission = Submission.from_message(input_message_bitstream_dspace_post_error)
    submission.submit()
    assert submission.result_message["ResultType"] == "error"
    assert submission.result_message["ErrorInfo"] == (
        "Error occurred while posting bitstream 'test-file-01.pdf' to item in DSpace. "
        "Item '0000/item02' and any bitstreams already posted to it will be deleted"
    )


@patch("submitter.submission.DSpace6Client")
def test_submit_dspace6_dspace_unknown_api_error_logs_exception_and_raises_error(
    mock_dspace_client,
    test_dspace6_client,
    caplog,
    mocked_dspace6,
    input_message_item_post_dspace_generic_500_error,
):
    mock_dspace_client.return_value = test_dspace6_client
    submission = Submission.from_message(input_message_item_post_dspace_generic_500_error)
    with pytest.raises(RequestException):
        submission.submit()
    # assert actual encountered exception is logged (for debugging purposes)
    assert (
        "Catastrophic error before or during request!  No response to parse."
        in caplog.text
    )
    # assert unhandled exception encountered in submit flow logged
    assert (
        "Unexpected exception, aborting DSpace Submission Service processing"
        in caplog.text
    )


def test_create_item_dspace8_success(dspace8_submission_instance):
    item = dspace8_submission_instance._create_item_dspace8()  # noqa: SLF001
    assert item.uuid == "item01"
    assert item.bitstreams[0].uuid == "bitstream01"
