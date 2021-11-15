from submitter import message


def test_generate_messages_from_file():
    messages = message.generate_submission_messages_from_file(
        "tests/fixtures/completely-fake-data.json", "empty_output_queue"
    )
    assert next(messages) == (
        {
            "PackageID": {"DataType": "String", "StringValue": "123"},
            "SubmissionSource": {"DataType": "String", "StringValue": "ETD"},
            "OutputQueue": {"DataType": "String", "StringValue": "empty_output_queue"},
        },
        '{"SubmissionSystem": "DSpace@MIT", "CollectionHandle": "1721.1/131022", '
        '"MetadataLocation": "s3:/fakeloc/a.json", "Files": [{"BitstreamName": '
        '"file 1", "FileLocation": "s3:/fakeloc2/f.json"}]}',
    )


def test_attributes_from_json():
    attributes = message.attributes_from_json(message_json, "empty_output_queue")
    assert attributes == {
        "PackageID": {
            "DataType": "String",
            "StringValue": "test-01",
        },
        "SubmissionSource": {
            "DataType": "String",
            "StringValue": "tests",
        },
        "OutputQueue": {
            "DataType": "String",
            "StringValue": "empty_output_queue",
        },
    }


def test_body_from_json():
    body = message.body_from_json(message_json)
    assert body == {
        "SubmissionSystem": "DSpace@MIT",
        "CollectionHandle": "1721.1/12345",
        "MetadataLocation": "tests/fixtures/test-item-metadata.json",
        "Files": [
            {
                "BitstreamName": "test-file-01.pdf",
                "FileLocation": "tests/fixtures/test-item-metadata.json",
                "BitstreamDescription": "A test bitstream",
            },
            {
                "BitstreamName": "test-file-01.pdf",
                "FileLocation": "tests/fixtures/test-item-metadata.json",
                "BitstreamDescription": "Another test bitstream",
            },
        ],
    }


message_json = {
    "package id": "test-01",
    "source": "tests",
    "target system": "DSpace@MIT",
    "collection handle": "1721.1/12345",
    "metadata location": "tests/fixtures/test-item-metadata.json",
    "files": [
        {
            "name": "test-file-01.pdf",
            "location": "tests/fixtures/test-item-metadata.json",
            "description": "A test bitstream",
        },
        {
            "name": "test-file-01.pdf",
            "location": "tests/fixtures/test-item-metadata.json",
            "description": "Another test bitstream",
        },
    ],
}
