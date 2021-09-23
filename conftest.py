import json
import os

import boto3
import pytest
import requests_mock
from dspace import DSpaceClient
from moto import mock_sqs


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(scope="function")
def mocked_dspace():
    with requests_mock.Mocker() as m:
        m.post(
            "mock://dspace.edu/rest/login",
            cookies={"JSESSIONID": "sessioncookie"},
        )
        m.get(
            "mock://dspace.edu/rest/handle/0000/collection01",
            json={"uuid": "collection01"},
        )
        m.post(
            "mock://dspace.edu/rest/collections/collection01/items",
            json=item_post_response,
        )
        m.post(
            "mock://dspace.edu/rest/items/item01/bitstreams",
            json=bitstream_post_response,
        )
        m.post(
            "mock://dspace.edu/rest/collections/not-a-collection/items", status_code=404
        )
        m.delete("mock://dspace.edu/rest/bitstreams/bitstream01", status_code=200)
        m.delete("mock://dspace.edu/rest/items/item01", status_code=200)
        yield m


@pytest.fixture(scope="function")
def mocked_sqs(aws_credentials):
    with mock_sqs():
        sqs = boto3.resource("sqs")
        sqs.create_queue(QueueName="empty_input_queue")
        sqs.create_queue(QueueName="empty_result_queue")
        queue = sqs.create_queue(QueueName="input_queue_with_messages")
        for i in range(11):
            queue.send_message(
                MessageAttributes=test_attributes,
                MessageBody=json.dumps(
                    {
                        "SubmissionSystem": "DSpace@MIT",
                        "CollectionHandle": "0000/collection01",
                        "MetadataLocation": "tests/fixtures/test-item-metadata.json",
                        "Files": [
                            {
                                "BitstreamName": "test-file-01.pdf",
                                "FileLocation": "tests/fixtures/test-file-01.pdf",
                                "BitstreamDescription": "A test bitstream",
                            }
                        ],
                    }
                ),
            )
        yield sqs


@pytest.fixture(scope="function")
def test_client(mocked_dspace):
    client = DSpaceClient("mock://dspace.edu/rest/")
    client.login("test", "test")
    yield client


@pytest.fixture
def input_message_good(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")
    queue.send_message(
        MessageAttributes=test_attributes,
        MessageBody=json.dumps(
            {
                "SubmissionSystem": "DSpace@MIT",
                "CollectionHandle": "0000/collection01",
                "MetadataLocation": "tests/fixtures/test-item-metadata.json",
                "Files": [
                    {
                        "BitstreamName": "test-file-01.pdf",
                        "FileLocation": "tests/fixtures/test-file-01.pdf",
                        "BitstreamDescription": "A test bitstream",
                    }
                ],
            }
        ),
    )
    message = queue.receive_messages(MessageAttributeNames=["All"])[0]
    yield message


@pytest.fixture
def input_message_item_create_error(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")
    queue.send_message(
        MessageAttributes=test_attributes,
        MessageBody=json.dumps(
            {
                "SubmissionSystem": "DSpace@MIT",
                "CollectionHandle": "0000/collection01",
                "MetadataLocation": "tests/fixtures/test-item-metadata-error.json",
                "Files": [
                    {
                        "BitstreamName": "test-file-01.pdf",
                        "FileLocation": "tests/fixtures/test-file-01.pdf",
                        "BitstreamDescription": "A test bitstream",
                    }
                ],
            }
        ),
    )
    message = queue.receive_messages(MessageAttributeNames=["All"])[0]
    yield message


@pytest.fixture
def input_message_bitstream_create_error(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")
    queue.send_message(
        MessageAttributes=test_attributes,
        MessageBody=json.dumps(
            {
                "SubmissionSystem": "DSpace@MIT",
                "CollectionHandle": "0000/collection01",
                "MetadataLocation": "tests/fixtures/test-item-metadata.json",
                "Files": [
                    {
                        "BitstreamName": "test-file-01.pdf",
                        "BitstreamDescription": "A test bitstream",
                    }
                ],
            }
        ),
    )
    message = queue.receive_messages(MessageAttributeNames=["All"])[0]
    yield message


@pytest.fixture
def input_message_item_post_error(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")
    queue.send_message(
        MessageAttributes=test_attributes,
        MessageBody=json.dumps(
            {
                "SubmissionSystem": "DSpace@MIT",
                "CollectionHandle": "0000/not-a-collection",
                "MetadataLocation": "tests/fixtures/test-item-metadata.json",
                "Files": [
                    {
                        "BitstreamName": "test-file-01.pdf",
                        "FileLocation": "tests/fixtures/test-file-01.pdf",
                        "BitstreamDescription": "A test bitstream",
                    }
                ],
            }
        ),
    )
    message = queue.receive_messages(MessageAttributeNames=["All"])[0]
    yield message


@pytest.fixture
def input_message_bitstream_post_error(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")
    queue.send_message(
        MessageAttributes=test_attributes,
        MessageBody=json.dumps(
            {
                "SubmissionSystem": "DSpace@MIT",
                "CollectionHandle": "0000/collection01",
                "MetadataLocation": "tests/fixtures/test-item-metadata.json",
                "Files": [
                    {
                        "BitstreamName": "test-file-01.pdf",
                        "FileLocation": "tests/fixtures/test-file-01.pdf",
                        "BitstreamDescription": "A test bitstream",
                    },
                    {
                        "BitstreamName": "No file",
                        "FileLocation": "tests/fixtures/nothing-here",
                        "BitstreamDescription": "No file",
                    },
                ],
            }
        ),
    )
    message = queue.receive_messages(MessageAttributeNames=["All"])[0]
    yield message


item_post_response = {
    "uuid": "item01",
    "name": "Test Thesis",
    "handle": "0000/item01",
    "type": "item",
    "link": "/rest/items/item01",
    "expand": [
        "metadata",
        "parentCollection",
        "parentCollectionList",
        "parentCommunityList",
        "bitstreams",
        "all",
    ],
    "lastModified": "2015-01-12 15:44:12.978",
    "parentCollection": None,
    "parentCollectionList": None,
    "parentCommunityList": None,
    "bitstreams": None,
    "archived": "true",
    "withdrawn": "false",
}

bitstream_post_response = {
    "uuid": "bitstream01",
    "name": "test-file-01.pdf",
    "handle": None,
    "type": "bitstream",
    "link": "/rest/bitstreams/bitstream01",
    "expand": ["parent", "policies", "all"],
    "bundleName": "ORIGINAL",
    "description": "A test bitstream",
    "format": "Adobe PDF",
    "mimeType": "application/pdf",
    "sizeBytes": 129112,
    "parentObject": None,
    "retrieveLink": "/bitstreams/bitstream01/retrieve",
    "checkSum": {
        "value": "62778292a3a6dccbe2662a2bfca3b86e",
        "checkSumAlgorithm": "MD5",
    },
    "sequenceId": 1,
    "policies": None,
}

test_attributes = {
    "PackageID": {"DataType": "String", "StringValue": "etdtest01"},
    "SubmissionSource": {"DataType": "String", "StringValue": "etd"},
    "OutputQueue": {
        "DataType": "String",
        "StringValue": "empty_result_queue",
    },
}
