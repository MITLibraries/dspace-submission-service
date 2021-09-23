import traceback

from dspace import Bitstream, Item
from freezegun import freeze_time

from submitter.submission import Submission


def test_init_submission_from_message(input_message_good):
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


def test_get_metadata_entries_from_file():
    submission = Submission(
        destination=None,
        collection_handle=None,
        metadata_location="tests/fixtures/test-item-metadata.json",
        files=None,
        attributes=None,
        result_queue=None,
    )
    metadata = submission.get_metadata_entries_from_file()
    assert next(metadata) == {"key": "dc.title", "value": "Test Thesis"}


@freeze_time("2021-09-01 05:06:07")
def test_result_error_message(input_message_good):
    submission = Submission.from_message(input_message_good)
    error = KeyError()
    submission.result_error_message(error, "A test error")
    assert submission.result_message["ResultType"] == "error"
    assert submission.result_message["ErrorTimestamp"] == "2021-09-01 05:06:07"
    assert submission.result_message["ErrorInfo"] == "A test error"
    assert submission.result_message["ExceptionMessage"] == str(error)
    assert submission.result_message["ExceptionTraceback"] == traceback.format_exc()


def test_result_success_message(input_message_good):
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


def test_submit_success(mocked_dspace, test_client, input_message_good):
    submission = Submission.from_message(input_message_good)
    submission.submit(test_client)
    assert submission.result_message["ResultType"] == "success"


def test_submit_create_item_error(
    mocked_dspace, test_client, input_message_item_create_error
):
    submission = Submission.from_message(input_message_item_create_error)
    submission.submit(test_client)
    assert submission.result_message["ResultType"] == "error"
    assert (
        submission.result_message["ErrorInfo"]
        == "Error occurred while creating item metadata from file"
    )


def test_submit_add_bitstreams_error(
    mocked_dspace, test_client, input_message_bitstream_create_error
):
    submission = Submission.from_message(input_message_bitstream_create_error)
    submission.submit(test_client)
    assert submission.result_message["ResultType"] == "error"
    assert (
        submission.result_message["ErrorInfo"]
        == "Error occurred while adding bitstreams to item from files"
    )


def test_submit_item_post_error(
    mocked_dspace, test_client, input_message_item_post_error
):
    submission = Submission.from_message(input_message_item_post_error)
    submission.submit(test_client)
    assert submission.result_message["ResultType"] == "error"
    assert (
        submission.result_message["ErrorInfo"]
        == "Error occurred while posting item to DSpace"
    )


def test_submit_bitstream_post_error(
    mocked_dspace, test_client, input_message_bitstream_post_error
):
    submission = Submission.from_message(input_message_bitstream_post_error)
    submission.submit(test_client)
    assert submission.result_message["ResultType"] == "error"
    assert submission.result_message["ErrorInfo"] == (
        "Error occurred while posting bitstreams to item in DSpace. Item with handle "
        "0000/item01 and any successfully posted bitstreams have been deleted"
    )
