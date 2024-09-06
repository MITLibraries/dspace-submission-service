import json
import logging
import sys
import traceback
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import dspace
import requests
import smart_open
from dspace.client import DSpaceClient

from submitter import CONFIG, errors

if TYPE_CHECKING:
    from mypy_boto3_sqs.service_resource import Message

logger = logging.getLogger(__name__)


class Submission:
    def __init__(
        self,
        attributes: dict,
        result_queue: str,
        *,
        result_message: dict | str | None = None,
        destination: str | None = None,
        collection_handle: str | None = None,
        metadata_location: str | None = None,
        files: list[dict] | None = None,
    ) -> None:
        self.destination = destination
        self.collection_handle = collection_handle
        self.metadata_location = metadata_location
        self.files = files
        self.result_attributes = attributes
        self.result_message = result_message
        self.result_queue = result_queue

    @classmethod
    def from_message(cls, message: "Message") -> "Submission":
        """
        Create a submission with all necessary publishing data from a submit message.

        Args:
            message: An SQS message

        Raises:
            SubmitMessageInvalidResultQueueError
            SubmitMessageMissingAttributeError
        """
        result_queue = message.message_attributes.get(  # type: ignore[call-overload]
            "OutputQueue", {}
        ).get("StringValue")
        if not result_queue or result_queue not in CONFIG.OUTPUT_QUEUES:
            raise errors.SubmitMessageInvalidResultQueueError(
                message.message_id, result_queue
            )

        try:
            attributes = {
                "PackageID": message.message_attributes["PackageID"],
                "SubmissionSource": message.message_attributes["SubmissionSource"],
            }
        except KeyError as e:
            raise errors.SubmitMessageMissingAttributeError(
                message.message_id, e.args[0]
            ) from e

        try:
            body = json.loads(message.body)
            destination = body["SubmissionSystem"]
            collection_handle = body["CollectionHandle"]
            metadata_location = body["MetadataLocation"]
            files = body["Files"]
        except (json.JSONDecodeError, KeyError, TypeError):
            result_message = (
                "Submission message did not conform to the DSS specification. Message "
                f"body provided was: '{message.body}'"
            )
            return cls(
                attributes,
                result_queue,
                result_message=result_message,
            )

        return cls(
            attributes,
            result_queue,
            destination=destination,
            collection_handle=collection_handle,
            metadata_location=metadata_location,
            files=files,
        )

    def create_item(self) -> dspace.item.Item:
        """Create item instance with metadata entries from submission message."""
        logger.debug("Creating local item instance from submission message")
        item = dspace.item.Item()
        try:
            for entry in self.get_metadata_entries_from_file():
                metadata_entry = dspace.item.MetadataEntry.from_dict(entry)
                item.metadata.append(metadata_entry)
        except KeyError as e:
            raise errors.ItemCreateError(self.metadata_location) from e
        return item

    def get_metadata_entries_from_file(self) -> Iterator[dict]:
        with smart_open.open(self.metadata_location) as f:
            metadata = json.load(f)
        yield from metadata["metadata"]

    def add_bitstreams_to_item(self, item: dspace.item.Item) -> dspace.item.Item:
        """Add bitstreams to item from files in submission message."""
        logger.debug("Adding bitstreams to local item instance from submission message")
        try:
            for file in self.files or []:
                bitstream = dspace.bitstream.Bitstream(
                    file_path=file["FileLocation"],
                    name=file["BitstreamName"],
                    description=file.get("BitstreamDescription"),
                )
                item.bitstreams.append(bitstream)
        except KeyError as e:
            raise errors.BitstreamAddError from e
        return item

    def result_error_message(
        self, message: str, dspace_response: str | None = None
    ) -> None:
        """Set result message on Submission object on submit error."""
        time = datetime.now(tz=UTC)
        tb = traceback.format_exception(*sys.exc_info())
        self.result_message = {
            "ResultType": "error",
            "ErrorTimestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ErrorInfo": message,
            "DSpaceResponse": dspace_response or "N/A",
            "ExceptionTraceback": prettify(tb),
        }

    def result_success_message(self, item: dspace.item.Item) -> None:
        """Set result message on Submission object on successful submit."""
        self.result_message = {
            "ResultType": "success",
            "ItemHandle": item.handle,
            "lastModified": item.lastModified,
            "Bitstreams": [],
        }

        for bitstream in item.bitstreams:
            self.result_message["Bitstreams"].append(
                {
                    "BitstreamName": bitstream.name,
                    "BitstreamUUID": bitstream.uuid,
                    "BitstreamChecksum": bitstream.checkSum,
                }
            )

    def submit(self, client: DSpaceClient) -> None:
        """Submit a submission to DSpace as a new item with associated bitstreams.

        Creates a local item instance from the submission message, adds bitstream
        objects, posts the item to DSpace, and posts each bitstream to the posted
        item. Creates result success message if successful, otherwise creates
        appropriate result error message based on the specific exception raised during
        submission.

        Raises:
            DSpaceTimeoutError: If the DSpace server takes longer than the
                configuration timeout setting to respond. Because this indicates a
                serious error on the DSpace side, rather than handling this exception
                it is re-raised with some useful message information and stops the
                entire SQS message loop process until someone can investigate further.
        """
        try:
            item = self.create_item()
            item = self.add_bitstreams_to_item(item)
            post_item(client, item, self.collection_handle)
            post_bitstreams(client, item)
            self.result_success_message(item)
        except requests.exceptions.Timeout as e:
            raise errors.DSpaceTimeoutError(
                client.base_url, self.result_attributes
            ) from e
        except (
            errors.ItemCreateError,
            errors.BitstreamAddError,
            errors.ItemPostError,
        ) as e:
            self.result_error_message(e.message, getattr(e, "dspace_error", None))
        except (errors.BitstreamOpenError, errors.BitstreamPostError) as e:
            self.result_error_message(e.message, getattr(e, "dspace_error", None))
            clean_up_partial_success(client, item)
        except Exception:
            logger.exception(
                "Unexpected exception, aborting DSpace Submission Service processing"
            )
            raise


def post_item(
    client: DSpaceClient,
    item: dspace.item.Item,
    collection_handle: str | None,
) -> None:
    """Post item with metadata to DSpace."""
    try:
        entries = [entry.to_dict() for entry in item.metadata]
        logger.debug(
            "Posting item to DSpace with metadata: %s",
            json.dumps(entries, indent=2),
        )
        item.post(client, collection_handle=collection_handle)
        logger.debug("Posted item to Dspace with handle '%s'", item.handle)
    except requests.exceptions.Timeout:
        raise
    except requests.exceptions.HTTPError as e:
        raise errors.ItemPostError(e, collection_handle) from e


def post_bitstreams(client: DSpaceClient, item: dspace.item.Item) -> None:
    """Post all bitstreams to an existing DSpace item."""
    logger.debug(
        "Posting %d bitstream(s) to item '%s' in DSpace",
        len(item.bitstreams),
        item.handle,
    )
    for bitstream in item.bitstreams:
        try:
            bitstream.post(client, item_uuid=item.uuid)
            logger.debug(
                "Posted bitstream '%s' to item '%s', new bitstream uuid is '%s'",
                bitstream.name,
                item.handle,
                bitstream.uuid,
            )
        except FileNotFoundError as e:
            raise errors.BitstreamOpenError(bitstream.file_path, item.handle) from e
        except requests.exceptions.HTTPError as e:
            raise errors.BitstreamPostError(e, bitstream.name, item.handle) from e


def clean_up_partial_success(client: DSpaceClient, item: dspace.item.Item) -> None:
    logger.info("Item '%s' was partially posted to DSpace, cleaning up", item.handle)
    handle = item.handle
    for bitstream in item.bitstreams:
        if bitstream.uuid is not None:
            uuid = bitstream.uuid
            bitstream.delete(client)
            logger.info("Bitstream '%s' deleted from DSpace", uuid)
    item.delete(client)
    logger.info("Item '%s' deleted from DSpace", handle)


def prettify(traceback: list) -> list[str]:
    output = []
    for item in traceback:
        lines = item.strip().split("\n")
        output.extend([line.strip().replace('\\"', "'") for line in lines])
    return output
