import json


def generate_submission_messages_from_file(filepath, output_queue):
    with open(filepath) as file:
        messages = json.load(file)

    for message_name, message_json in messages.items():
        attributes = attributes_from_json(message_json, output_queue)
        body = body_from_json(message_json)
        yield attributes, body


def attributes_from_json(message_json, output_queue):
    attributes = {
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
    return attributes


def body_from_json(message_json):
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


def generate_result_messages_from_file(filepath, output_queue):
    with open(filepath) as file:
        messages = json.load(file)

    for message_name, message_json in messages.items():
        attributes = result_attributes_from_json(message_json)
        body = result_body_from_json(message_json)
        yield attributes, body


def result_attributes_from_json(message_json):
    attributes = {
        "PackageID": {
            "DataType": "String",
            "StringValue": message_json["package id"],
        },
        "SubmissionSource": {
            "DataType": "String",
            "StringValue": message_json["source"],
        },
    }
    return attributes


def result_body_from_json(message_json):
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
