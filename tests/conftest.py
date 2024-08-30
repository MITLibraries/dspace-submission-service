# ruff: noqa: PT004, S105

import json
import os

import boto3
import pytest
import requests_mock
from dspace import DSpaceClient
from moto import mock_aws
from requests import exceptions


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"


@pytest.fixture
def test_aws_user(aws_credentials):
    with mock_aws():
        user_name = "test-user"
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:ListBucket", "sqs:GetQueueUrl"],
                    "Resource": "*",
                },
                {
                    "Effect": "Deny",
                    "Action": [
                        "s3:GetObject",
                        "sqs:ReceiveMessage",
                        "sqs:SendMessage",
                    ],
                    "Resource": "*",
                },
            ],
        }
        client = boto3.client("iam", region_name="us-east-1")
        client.create_user(UserName=user_name)
        client.put_user_policy(
            UserName=user_name,
            PolicyName="policy1",
            PolicyDocument=json.dumps(policy_document),
        )
        yield client.create_access_key(UserName="test-user")["AccessKey"]


@pytest.fixture
def mocked_dspace():
    """The following mock responses from DSpace based on the URL of the request.

    Fixtures below that prepare an SQS message, where specific collections or bitstreams
    are included, will utilize these mocked responses from DSpace.

    EXAMPLE: fixture 'input_message_item_post_dspace_timeout' sets collection
    "CollectionHandle: 0000/collection03".  This aligns with a URL defined here, and will
    therefore throw a requests.exceptions.ConnectTimeout exception to test against.
    """
    with requests_mock.Mocker() as m:
        m.post(
            "mock://dspace.edu/rest/login",
            cookies={"JSESSIONID": "sessioncookie"},
        )
        m.get(
            "mock://dspace.edu/rest/handle/0000/collection01",
            json={"uuid": "collection01"},
        )
        m.get(
            "mock://dspace.edu/rest/handle/0000/collection02",
            json={"uuid": "collection02"},
        )
        m.get(
            "mock://dspace.edu/rest/handle/0000/collection03",
            exc=exceptions.ConnectTimeout,
        )
        m.get(
            "mock://dspace.edu/rest/handle/0000/collection04",
            exc=exceptions.RequestException(
                "Catastrophic error before or during request!  No response to parse."
            ),
        )
        m.get(
            "mock://dspace.edu/rest/handle/0000/not-a-collection",
            status_code=404,
        )
        m.post(
            "mock://dspace.edu/rest/collections/collection01/items",
            json=item_post_response_01,
        )
        m.post(
            "mock://dspace.edu/rest/collections/collection02/items",
            json=item_post_response_02,
        )
        m.post(
            "mock://dspace.edu/rest/items/item01/bitstreams",
            json=bitstream_post_response,
        )
        m.post(
            "mock://dspace.edu/rest/items/item02/bitstreams",
            status_code=500,
        )
        m.delete("mock://dspace.edu/rest/bitstreams/bitstream01", status_code=200)
        m.delete("mock://dspace.edu/rest/items/item01", status_code=200)
        m.delete("mock://dspace.edu/rest/items/item02", status_code=200)
        yield m


@pytest.fixture
def mocked_dspace_auth_failure():
    with requests_mock.Mocker() as m:
        m.post("mock://dspace.edu/rest/login", status_code=401)
        yield m


@pytest.fixture
def mocked_sqs(aws_credentials):
    with mock_aws():
        sqs = boto3.resource("sqs")
        sqs.create_queue(QueueName="empty_input_queue")
        sqs.create_queue(QueueName="empty_result_queue")
        queue = sqs.create_queue(QueueName="input_queue_with_messages")
        for _i in range(11):
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
        bad_queue = sqs.create_queue(QueueName="bad_input_messages")
        bad_queue.send_message(
            MessageAttributes=test_attributes,
            MessageBody="Doesn't conform to the DSS spec",
        )
        yield sqs


@pytest.fixture
def mocked_s3(aws_credentials):
    with mock_aws():
        s3 = boto3.client("s3")
        s3.create_bucket(
            Bucket="test-bucket",
        )
        s3.put_object(Bucket="test-bucket", Key="object1", Body="I am an object.")
        yield s3


@pytest.fixture
def test_client(mocked_dspace):
    client = DSpaceClient("mock://dspace.edu/rest/")
    client.login("test", "test")
    return client


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
    return queue.receive_messages(MessageAttributeNames=["All"])[0]


@pytest.fixture
def input_message_nonconforming_body(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")
    queue.send_message(
        MessageAttributes=test_attributes,
        MessageBody="Doesn't conform to the DSS spec",
    )
    return queue.receive_messages(MessageAttributeNames=["All"])[0]


@pytest.fixture
def input_message_invalid_queue(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")
    queue.send_message(
        MessageAttributes={
            "PackageID": {"DataType": "String", "StringValue": "etdtest01"},
            "SubmissionSource": {"DataType": "String", "StringValue": "etd"},
            "OutputQueue": {
                "DataType": "String",
                "StringValue": "not-a-queue",
            },
        },
        MessageBody="irrelevant",
    )
    return queue.receive_messages(MessageAttributeNames=["All"])[0]


@pytest.fixture
def input_message_missing_attribute(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")
    queue.send_message(
        MessageAttributes={
            "PackageID": {"DataType": "String", "StringValue": "etdtest01"},
            "OutputQueue": {
                "DataType": "String",
                "StringValue": "empty_result_queue",
            },
        },
        MessageBody="irrelevant",
    )
    return queue.receive_messages(MessageAttributeNames=["All"])[0]


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
    return queue.receive_messages(MessageAttributeNames=["All"])[0]


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
    return queue.receive_messages(MessageAttributeNames=["All"])[0]


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
    return queue.receive_messages(MessageAttributeNames=["All"])[0]


@pytest.fixture
def input_message_item_post_dspace_timeout(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")
    queue.send_message(
        MessageAttributes=test_attributes,
        MessageBody=json.dumps(
            {
                "SubmissionSystem": "DSpace@MIT",
                "CollectionHandle": "0000/collection03",
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
    return queue.receive_messages(MessageAttributeNames=["All"])[0]


@pytest.fixture
def input_message_bitstream_file_open_error(mocked_sqs):
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
    return queue.receive_messages(MessageAttributeNames=["All"])[0]


@pytest.fixture
def input_message_item_post_dspace_generic_500_error(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")
    queue.send_message(
        MessageAttributes=test_attributes,
        MessageBody=json.dumps(
            {
                "SubmissionSystem": "DSpace@MIT",
                "CollectionHandle": "0000/collection04",
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
    return queue.receive_messages(MessageAttributeNames=["All"])[0]


@pytest.fixture
def input_message_bitstream_dspace_post_error(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")
    queue.send_message(
        MessageAttributes=test_attributes,
        MessageBody=json.dumps(
            {
                "SubmissionSystem": "DSpace@MIT",
                "CollectionHandle": "0000/collection02",
                "MetadataLocation": "tests/fixtures/test-item-metadata.json",
                "Files": [
                    {
                        "BitstreamName": "test-file-01.pdf",
                        "FileLocation": "tests/fixtures/test-file-01.pdf",
                        "BitstreamDescription": "A test bitstream",
                    },
                ],
            }
        ),
    )
    return queue.receive_messages(MessageAttributeNames=["All"])[0]


@pytest.fixture
def raw_attributes():
    return test_attributes


@pytest.fixture
def raw_body():
    return {
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


@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    monkeypatch.setenv("WORKSPACE", "test")
    monkeypatch.setenv("DSPACE_API_URL", "mock://dspace.edu/rest/")
    monkeypatch.setenv("DSPACE_USER", "test")
    monkeypatch.setenv("DSPACE_PASSWORD", "test")
    monkeypatch.setenv("DSPACE_TIMEOUT", "3.0")
    monkeypatch.setenv("INPUT_QUEUE", "input_queue")
    monkeypatch.setenv("LOG_FILTER", "false")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("SENTRY_DSN", "mock://12345.6789.sentry")
    monkeypatch.setenv("SKIP_PROCESSING", "true")
    monkeypatch.setenv("SQS_ENDPOINT_URL", "https://sqs.us-east-1.amazonaws.com/")
    monkeypatch.setenv("OUTPUT_QUEUES", "output_queue_1,output_queue_2")


item_post_response_01 = {
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

item_post_response_02 = {
    "uuid": "item02",
    "name": "Test Thesis",
    "handle": "0000/item02",
    "type": "item",
    "link": "/rest/items/item02",
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
