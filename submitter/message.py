import json
from collections.abc import Iterator


def generate_submission_messages_from_file(
    filepath: str, output_queue: str
) -> Iterator[tuple[dict, dict]]:
    with open(filepath) as file:
        messages = json.load(file)

    for message_json in messages.values():
        attributes = attributes_from_json(message_json, output_queue)
        body = body_from_json(message_json)
        yield attributes, body


def attributes_from_json(message_json: dict, output_queue: str) -> dict:
    return {
        "PackageID": {
            "DataType": "String",
            "StringValue": message_json["package id"],
        },
        "SubmissionSource": {
            "DataType": "String",
            "StringValue": message_json["source"],
        },
        "OutputQueue": {
            "DataType": "String",
            "StringValue": output_queue,
        },
    }


def body_from_json(message_json: dict) -> dict:
    body = {
        "SubmissionSystem": message_json["target system"],
        "CollectionHandle": message_json["collection handle"],
        "MetadataLocation": message_json["metadata location"],
        "Files": [],
    }
    for file_json in message_json["files"]:
        bitstream_data = {
            "BitstreamName": file_json.get("name"),
            "FileLocation": file_json.get("location"),
            "BitstreamDescription": file_json.get("description"),
        }
        body["Files"].append({k: v for k, v in bitstream_data.items() if v is not None})
    return body


def generate_result_messages_from_file(
    filepath: str, _output_queue: str
) -> Iterator[tuple[dict, dict]]:
    with open(filepath) as file:
        messages = json.load(file)

    for message_json in messages.values():
        attributes = result_attributes_from_json(message_json)
        body = result_body_from_json(message_json)
        yield attributes, body


def result_attributes_from_json(message_json: dict) -> dict:
    return {
        "PackageID": {
            "DataType": "String",
            "StringValue": message_json["package id"],
        },
        "SubmissionSource": {
            "DataType": "String",
            "StringValue": message_json["source"],
        },
    }


def result_body_from_json(message_json: dict) -> dict:
    body = {
        "ResultType": message_json["result"],
        "ItemHandle": message_json["handle"],
        "lastModified": message_json["modified"],
        "Bitstreams": [],
    }
    for file_json in message_json["files"]:
        bitstream_data = {
            "BitstreamName": file_json.get("bitstream name"),
            "BitstreamUUID": file_json.get("uuid"),
            "BitstreamChecksum": file_json.get("checksum"),
        }
        body["Bitstreams"].append(
            {k: v for k, v in bitstream_data.items() if v is not None}
        )
    return body
