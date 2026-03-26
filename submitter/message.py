import json
import logging
from collections.abc import Iterator
from functools import lru_cache
from typing import TYPE_CHECKING

import jsonschema

if TYPE_CHECKING:
    from mypy_boto3_sqs.service_resource import Message

from submitter import errors
from submitter.config import Config

logger = logging.getLogger(__name__)
CONFIG = Config()


@lru_cache
def load_jsonschemas() -> dict:
    """Load SQS message attributes and body JSON Schema docs."""
    logger.debug("Loading JSON schemas to cache")

    # load SQS message attributes validation schema
    with open("submitter/schemas/submission-message-attributes.json") as file:
        attributes_schema = json.load(file)
        # set constraint on "OutputQueue" using CONFIG
        attributes_schema["properties"]["OutputQueue"]["properties"]["StringValue"][
            "enum"
        ] = CONFIG.output_queues

    # load SQS message body validation schema
    with open("submitter/schemas/submission-message-body.json") as file:
        body_schema = json.load(file)

    return {
        "submission-message-attributes": attributes_schema,
        "submission-message-body": body_schema,
    }


def validate_message(message: "Message") -> tuple[dict, dict]:
    schemas = load_jsonschemas()

    # validate message attributes
    try:
        jsonschema.validate(
            instance=message.message_attributes,
            schema=schemas["submission-message-attributes"],
        )
    except jsonschema.ValidationError as exception:
        raise errors.SubmissionMessageAttributesValidationError(
            exception.message
        ) from exception

    # parse and validate message body JSON string
    try:
        body = json.loads(message.body)
        jsonschema.validate(instance=body, schema=schemas["submission-message-body"])
    except json.JSONDecodeError as exception:
        error_message = (
            "Unable to parse submission message body. Message "
            f"body provided was: '{message.body}'"
        )
        raise errors.SubmissionMessageBodyValidationError(error_message) from exception
    except jsonschema.ValidationError as exception:
        raise errors.SubmissionMessageBodyValidationError(
            exception.message
        ) from exception

    return message.message_attributes, body


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
