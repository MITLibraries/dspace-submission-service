# ruff: noqa: S105

import json
import os

import boto3
import pytest
import requests_mock
from dspace_rest_client.client import DSpaceClient
from moto import mock_aws

from submitter.sqs import _sqs_queues
from submitter.submission import Submission, dspace_clients


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
        # DSpace 8 URLs
        m.post("mock://dspace.edu/server/api/authn/login")
        m.get("mock://dspace.edu/server/api/authn/status", json={"authenticated": True})
        m.get("mock://dspace.edu/server/api/pid/find", json={"uuid": "collection01"})
        m.post(
            "mock://dspace.edu/server/api/core/items",
            json={
                "uuid": "item01",
                "handle": "0000/item01",
                "_links": {
                    "self": {"href": "mock://dspace.edu/server/api/core/items/item01"}
                },
            },
        )
        m.delete("mock://dspace.edu/server/api/core/items/item01", status_code=200)
        m.post(
            "mock://dspace.edu/server/api/core/items/item01/bundles",
            json={
                "uuid": "bundle01",
                "name": "ORIGINAL",
                "_links": {
                    "self": {
                        "href": "mock://dspace.edu/server/api/core/bundles/bundle01"
                    },
                    "bitstreams": {
                        "href": "mock://dspace.edu/server/api/core/bundles/bundle01/bitstreams"
                    },
                },
            },
        )
        m.get(
            "mock://dspace.edu/server/api/core/bundles/bundle01",
            json={
                "uuid": "bundle01",
                "name": "ORIGINAL",
                "_links": {
                    "self": {
                        "href": "mock://dspace.edu/server/api/core/bundles/bundle01"
                    },
                    "bitstreams": {
                        "href": "mock://dspace.edu/server/api/core/bundles/bundle01/bitstreams"
                    },
                },
            },
        )
        m.post(
            "mock://dspace.edu/server/api/core/bundles/bundle01/bitstreams",
            json={
                "uuid": "bitstream01",
                "name": "test-file-01.pdf",
                "checkSum": "62778292a3a6dccbe2662a2bfca3b86e",
                "checkSumAlgorithm": "MD5",
            },
        )
        m.get(
            "mock://dspace.edu/server/api/core/bundles/bundle01/bitstreams",
            json={
                "_embedded": {
                    "bitstreams": [
                        {
                            "uuid": "bitstream01",
                            "name": "test-file-01.pdf",
                            "checkSum": "62778292a3a6dccbe2662a2bfca3b86e",
                            "checkSumAlgorithm": "MD5",
                        }
                    ]
                },
                "page": {
                    "size": 20,
                    "totalElements": 1,
                    "totalPages": 1,
                    "number": 0,
                },
            },
        )
        yield m


@pytest.fixture
def mocked_dspace_auth_failure():
    with requests_mock.Mocker() as m:
        m.post("mock://dspace.edu/server/api/authn/login", status_code=401)
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
                        "SubmissionSystem": "IR-8",
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
def dspace_client(mocked_dspace):
    client = DSpaceClient(
        api_endpoint="mock://dspace.edu/server/api",
        username="test",
        password="test",  # noqa: S106
        fake_user_agent=True,
    )
    client.authenticate()
    return client


@pytest.fixture(autouse=True)
def clear_dspace_client_cache():
    """Clear the DSpace client cache before each test."""
    dspace_clients.clear()


@pytest.fixture(autouse=True)
def clear_sqs_queue_cache():
    """Clear the SQS queue cache before each test."""
    _sqs_queues.clear()


@pytest.fixture
def dspace_submission_instance(dspace_client):
    submission = Submission(
        destination="DSpace@MIT",
        collection_handle="0000/collection01",
        metadata_location="tests/fixtures/test-item-metadata.json",
        files=[
            {
                "BitstreamName": "test-file-01.pdf",
                "FileLocation": "tests/fixtures/test-file-01.pdf",
                "BitstreamDescription": "A test bitstream",
            },
            {
                "BitstreamName": "test-file-02.pdf",
                "FileLocation": "tests/fixtures/test-file-01.pdf",
                "BitstreamDescription": "Another test bitstream",
            },
        ],
        result_queue=None,
        attributes={},
    )
    submission.client = dspace_client
    return submission


@pytest.fixture
def input_message_good_ddc8(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")
    queue.send_message(
        MessageAttributes=test_attributes,
        MessageBody=json.dumps(
            {
                "SubmissionSystem": "DDC-8",
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
def input_message_good_dspace_mit(mocked_sqs):
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
def input_message_missing_collection_handle(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")
    queue.send_message(
        MessageAttributes=test_attributes,
        MessageBody=json.dumps(
            {
                "SubmissionSystem": "IR-8",
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
def input_message_invalid_json(mocked_sqs):
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
                "SubmissionSystem": "IR-8",
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
    monkeypatch.setenv(
        "DSS_DSPACE_CREDENTIALS",
        json.dumps(
            {
                "ir-8": {
                    "url": "mock://dspace.edu/server/api",
                    "user": "test",
                    "password": "test",
                },
                "ddc-8": {
                    "url": "mock://dspace.edu/server/api",
                    "user": "test",
                    "password": "test",
                },
            }
        ),
    )
    monkeypatch.setenv("INPUT_QUEUE", "input_queue")
    monkeypatch.setenv("OUTPUT_QUEUES", "empty_result_queue")
    monkeypatch.setenv("SENTRY_DSN", "https://1234567890@00000.ingest.sentry.io/123456")
    monkeypatch.setenv("DSPACE_TIMEOUT", "3")
    monkeypatch.setenv("SKIP_PROCESSING", "false")
    monkeypatch.setenv("SQS_ENDPOINT_URL", "https://sqs.us-east-1.amazonaws.com/")


test_attributes = {
    "PackageID": {"DataType": "String", "StringValue": "etdtest01"},
    "SubmissionSource": {"DataType": "String", "StringValue": "etd"},
    "OutputQueue": {
        "DataType": "String",
        "StringValue": "empty_result_queue",
    },
}
