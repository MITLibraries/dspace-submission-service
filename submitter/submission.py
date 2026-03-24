# ruff: noqa: TD002, TD003, FIX002
import json
import logging
import os
import sys
import traceback
from collections.abc import Iterator
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

import dspace
import requests
import smart_open
from dspace.client import (
    DSpaceClient as DSpace6Client,
)  # Update after DSpace 8 migration
from dspace.item import Item as DSpace6Item  # Update after DSpace 8 migration
from dspace_rest_client.client import (
    DSpaceClient as DSpace8Client,
)  # Update after DSpace 8 migration
from dspace_rest_client.models import (
    Bundle as DSpace8Bundle,
)  # Update after DSpace 8 migration
from dspace_rest_client.models import Item as DSpace8Item

from submitter import errors
from submitter.config import Config
from submitter.message import validate_message

if TYPE_CHECKING:
    from mypy_boto3_sqs.service_resource import Message

logger = logging.getLogger(__name__)
CONFIG = Config()

# Shared cache for DSpace clients across all Submission instances
dspace_clients: dict[str, DSpace6Client | DSpace8Client] = (
    {}
)  # Update after DSpace 8 migration


class ValidItemOperations(StrEnum):
    CREATE = "create"
    UPDATE = "update"


class Submission:
    def __init__(
        self,
        attributes: dict,
        result_queue: str,
        *,
        result_message: dict | str | None = None,
        destination: str | None = None,
        operation: (
            Literal[ValidItemOperations.CREATE, ValidItemOperations.UPDATE] | None
        ) = ValidItemOperations.CREATE,
        collection_handle: str | None = None,
        item_handle: str | None = None,
        metadata_location: str | None = None,
        files: list[dict] | None = None,
    ) -> None:
        self.destination = destination
        self.operation = operation
        self.collection_handle = collection_handle
        self.item_handle = item_handle
        self.metadata_location = metadata_location
        self.files = files
        self.result_attributes = attributes
        self.result_message = result_message
        self.result_queue = result_queue

    def submit(self) -> None:
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
        if CONFIG.skip_processing != "true":
            self.client = self.get_dspace_client()
            logger.debug("Current clients in cache: %s", list(dspace_clients.keys()))

        try:
            if self.destination in [
                "DSpace@MIT",
                "DDC-6",
            ]:  # Update after DSpace 8 migration
                item = self._submit_item_dspace6()
                self.result_success_message(item)
            elif self.destination in ["IR-8", "DDC-8"]:
                item, bundle = self._submit_item_dspace8()
                self.result_success_message(item, bundle)

        # Expected exception, generate error message and continue
        except (
            errors.SubmissionError,
            errors.ItemPostError,  # Update after DSpace 8 migration
            errors.BitstreamOpenError,  # Update after DSpace 8 migration
            errors.BitstreamPostError,  # Update after DSpace 8 migration
        ) as e:
            self.result_error_message(e.message, getattr(e, "dspace_error", None))

        # DSpace timeout error, abort
        except requests.exceptions.Timeout as e:
            dspace_url = self.client.base_url if self.client else "Unknown DSpace URL"
            raise errors.DSpaceTimeoutError(dspace_url, self.result_attributes) from e

        # Unexpected exception, abort
        except Exception:
            logger.exception(
                "Unexpected exception, aborting DSpace Submission Service processing"
            )
            raise

    def get_dspace_client(
        self,
    ) -> DSpace6Client | DSpace8Client:  # Update after DSpace 8 migration
        """Create or get a cached DSpace client for the submission destination."""
        if not self.destination:
            raise errors.InvalidDSpaceDestinationError(self.destination)
        logger.debug(f"Getting DSpace client for destination '{self.destination}'")
        if self.destination not in dspace_clients:
            client = self._create_dspace_client(self.destination)
            dspace_clients[self.destination] = client
        else:
            logger.debug(
                f"Using cached DSpace client for destination '{self.destination}'"
            )
        return dspace_clients[self.destination]

    def _create_dspace_client(
        self, destination: str
    ) -> DSpace6Client | DSpace8Client:  # Update after DSpace 8 migration
        """Create a DSpace client for the submission destination."""
        logger.debug(f"Creating DSpace client for destination '{destination}'")
        try:
            credentials = CONFIG.dspace_credentials[destination]
        except KeyError as exc:
            raise errors.InvalidDSpaceDestinationError(destination) from exc
        if destination in ["DSpace@MIT", "DDC-6"]:  # Update after DSpace 8 migration
            return self._create_dspace6_client(credentials)
        elif destination in ["IR-8", "DDC-8"]:  # noqa: RET505
            return self._create_dspace8_client(credentials)
        raise ValueError(f"Destination value not recognized: {destination}")

    def _create_dspace6_client(
        self, credentials: dict[str, str | float | None]
    ) -> DSpace6Client:
        """Create and authenticate a DSpace 6 client."""
        client = DSpace6Client(credentials["url"], timeout=CONFIG.dspace_timeout)
        client.login(credentials["user"], credentials["password"])
        logger.info(
            f'Successfully authenticated to "{credentials["url"]}" as '
            f'"{credentials["user"]}"'
        )
        return client

    def _create_dspace8_client(
        self, credentials: dict[str, str | float | None]
    ) -> DSpace8Client:
        """Create and authenticate a DSpace 8 client."""
        client = DSpace8Client(
            api_endpoint=credentials["url"],
            username=credentials["user"],
            password=credentials["password"],
            fake_user_agent=True,
        )
        authenticated = client.authenticate()
        if not authenticated:
            raise errors.DSpaceAuthenticationError(
                credentials["url"], credentials["user"]
            )
        logger.info(
            f'Successfully authenticated to "{credentials["url"]}" as '
            f'"{credentials["user"]}"'
        )
        return client

    @classmethod
    def from_message(cls, message: "Message") -> "Submission":
        """
        Create a submission with all necessary publishing data from a submit message.

        Args:
            message: An SQS message

        Raises:
            SubmissionMessageAttributesValidationError
            SubmissionMessageBodyValidationError
        """
        try:
            message_attributes, message_body = validate_message(message)
        except errors.SubmissionMessageBodyValidationError as exception:
            result_queue = message.message_attributes.pop("OutputQueue")["StringValue"]
            return cls(
                attributes=message.message_attributes,
                result_queue=result_queue,
                result_message=str(exception),
            )

        result_queue = message_attributes.pop("OutputQueue")["StringValue"]
        operation = message_body.get("Operation", ValidItemOperations.CREATE)

        if operation == ValidItemOperations.UPDATE:
            return cls(
                attributes=message_attributes,
                result_queue=result_queue,
                destination=message_body["SubmissionSystem"],
                operation=operation,
                item_handle=message_body["ItemHandle"],
                metadata_location=message_body["MetadataLocation"],
                files=message_body["Files"],
            )
        return cls(
            attributes=message_attributes,
            result_queue=result_queue,
            destination=message_body["SubmissionSystem"],
            operation=operation,
            collection_handle=message_body["CollectionHandle"],
            metadata_location=message_body["MetadataLocation"],
            files=message_body["Files"],
        )

    def _submit_item_dspace6(  # Update after DSpace 8 migration
        self,
    ) -> DSpace6Item:
        """Create item instance with metadata entries from submission message."""
        logger.debug("Creating local item instance from submission message")
        item = DSpace6Item()
        try:
            for entry in self._get_metadata_entries_from_file_dspace6():
                metadata_entry = dspace.item.MetadataEntry.from_dict(entry)
                item.metadata.append(metadata_entry)
        except KeyError as e:
            raise errors.ItemError(
                message=(
                    "Error occurred while creating item metadata entries from file "
                    f"'{self.metadata_location}'"
                ),
                exception=e,
            ) from e

        item = self._add_bitstreams_to_item_dspace6(item)
        self._post_item_dspace6(item, self.collection_handle)
        self._post_bitstreams_dspace6(item)
        return item

    def _get_metadata_entries_from_file_dspace6(  # Update after DSpace 8 migration
        self,
    ) -> Iterator[dict]:
        with smart_open.open(self.metadata_location) as f:
            metadata = json.load(f)
        yield from metadata["metadata"]

    def _add_bitstreams_to_item_dspace6(  # Update after DSpace 8 migration
        self, item: DSpace6Item
    ) -> DSpace6Item:
        """Add bitstreams to item from files in submission message."""
        logger.debug("Adding bitstreams to local item instance from submission message")

        for file in self.files or []:
            bitstream = dspace.bitstream.Bitstream(
                file_path=file["FileLocation"],
                name=file["BitstreamName"],
                description=file.get("BitstreamDescription"),
            )
            item.bitstreams.append(bitstream)
        return item

    def _post_item_dspace6(  # Update after DSpace 8 migration
        self,
        item: DSpace6Item,
        collection_handle: str | None,
    ) -> None:
        """Post item with metadata to DSpace."""
        try:
            entries = [entry.to_dict() for entry in item.metadata]
            logger.debug(
                "Posting item to DSpace with metadata: %s",
                json.dumps(entries, indent=2),
            )
            item.post(self.client, collection_handle=collection_handle)
            logger.debug("Posted item to Dspace with handle '%s'", item.handle)
        except requests.exceptions.Timeout:
            raise
        except requests.exceptions.HTTPError as e:
            raise errors.ItemPostError(e, collection_handle) from e

    def _post_bitstreams_dspace6(  # Update after DSpace 8 migration
        self, item: DSpace6Item
    ) -> None:
        """Post all bitstreams to an existing DSpace item."""
        logger.debug(
            "Posting %d bitstream(s) to item '%s' in DSpace",
            len(item.bitstreams),
            item.handle,
        )
        for bitstream in item.bitstreams:
            try:
                bitstream.post(self.client, item_uuid=item.uuid)
                logger.debug(
                    "Posted bitstream '%s' to item '%s', new bitstream uuid is '%s'",
                    bitstream.name,
                    item.handle,
                    bitstream.uuid,
                )
            except (FileNotFoundError, requests.exceptions.RequestException) as e:
                partial_item_handle = item.handle
                self.clean_up_partial_success_dspace6(item)
                if isinstance(e, FileNotFoundError):
                    raise errors.BitstreamOpenError(
                        bitstream.file_path, partial_item_handle
                    ) from e
                raise errors.BitstreamPostError(
                    e, bitstream.name, partial_item_handle
                ) from e

    def _submit_item_dspace8(self) -> tuple[DSpace8Item, DSpace8Bundle]:
        """Submit item instance from submission message."""
        item = self._create_item_dspace8()
        bundle = self._create_bundle_dspace8(item)
        for bitstream_uri in self.files or []:
            self._create_bitstream_dspace8(item, bundle, bitstream_uri)
        return item, bundle

    def _create_item_dspace8(self) -> DSpace8Item:
        """Create item in DSpace from submission message.

        Note: Separate try-except blocks is are added to distinguish any errors
        related to accessing and opening the file in S3 from errors related
        requests to the DSpace server. For the former, the exception is not
        passed to ItemError to avoid incorrect assignment to Submission.dspace_error.
        """
        # check whether the collection exists
        collection = self.client.resolve_identifier_to_dso(
            identifier=self.collection_handle
        )
        if self.collection_handle and not collection:
            raise errors.DSpaceObjectNotFoundError(identifier=self.collection_handle)

        try:
            with smart_open.open(self.metadata_location, "r") as metadata:
                item_data = {
                    "metadata": json.load(metadata),
                    "discoverable": True,
                    "type": "item",
                }
        except Exception as e:
            logger.exception("Error creating item:")
            raise errors.ItemError(
                message=f"Failed to load metadata from {self.metadata_location}"
            ) from e

        try:
            item = self.client.create_item(
                parent=collection.uuid,
                item=DSpace8Item(item_data),
            )
        except Exception as e:
            logger.exception("Error creating item:")
            raise errors.ItemError(
                message=(
                    "Error occurred while creating item from file "
                    f"'{self.metadata_location}'"
                ),
                exception=e,
            ) from e

        # TODO: This check is added to raise an exception when the returned
        # Item object's handle is None. Should be updated if/when dspace-rest-python
        # is updated to raise exceptions.
        if item.handle is None:
            logger.exception("Error creating item:")
            raise errors.ItemError(
                message=(
                    "Error occurred while creating item from file "
                    f"'{self.metadata_location}'"
                )
            )

        logger.info(f"Item created with handle: {item.handle}")
        return item

    def _create_bundle_dspace8(self, item: DSpace8Item) -> DSpace8Bundle:
        """Create ORIGINAL bundle for a specified item."""
        try:
            bundle = self.client.create_bundle(parent=item, name="ORIGINAL")
        except Exception as e:
            logger.exception("Error creating bundle:")
            self.clean_up_partial_success_dspace8(item)
            raise errors.BundleError(
                message=(
                    f"Error occurred while creating bundle for item '{item.handle}' "
                    "in DSpace. Item and any bitstreams already posted to it will be deleted"  # noqa: E501
                ),
                exception=e,
            ) from e

        # TODO: This check is added to raise an exception when the returned
        # Bundle object's uuid is None. Should be updated if/when dspace-rest-python
        # is updated to raise exceptions.
        if bundle.uuid is None:
            logger.exception("Error creating bundle:")
            self.clean_up_partial_success_dspace8(item)
            raise errors.BundleError(
                message=(
                    f"Error occurred while creating bundle for item '{item.handle}' "
                    "in DSpace. Item and any bitstreams already posted to it will be deleted"  # noqa: E501
                )
            )

        logger.info(f"Bundle created with UUID: {bundle.uuid}")
        return bundle

    def _create_bitstream_dspace8(
        self, item: DSpace8Item, bundle: DSpace8Bundle, bitstream_data: dict
    ) -> None:
        """Create bitstream for a specified item bundle."""
        try:
            bitstream = self.client.create_bitstream(
                bundle=bundle,
                name=os.path.basename(bitstream_data["BitstreamName"]),
                path=bitstream_data["FileLocation"],
            )
        except Exception as e:
            logger.exception("Error creating bitstream:")
            self.clean_up_partial_success_dspace8(item)
            raise errors.BitstreamError(
                message=(
                    "Error occurred while creating bitstream from file "
                    f"'{bitstream_data["BitstreamName"]}' for item '{item.handle}'"
                ),
                exception=e,
            ) from e

        # TODO: This check is added to raise an exception when the client
        # returns None. Should be updated if/when dspace-rest-python
        # is updated to raise exceptions.
        if bitstream is None:
            logger.exception("Error creating bitstream:")
            self.clean_up_partial_success_dspace8(item)
            raise errors.BitstreamError(
                message=(
                    "Error occurred while creating bitstream from file "
                    f"'{bitstream_data["BitstreamName"]}' for item '{item.handle}'"
                ),
            )

        logger.info(f"Bitstream created with UUID: {bitstream.uuid}")

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

    def result_success_message(
        self, item: DSpace6Item | DSpace8Item, bundle: DSpace8Bundle | None = None
    ) -> None:
        """Set result message on Submission object on successful submit."""
        self.result_message = {
            "ResultType": "success",
            "ItemHandle": item.handle,
            "lastModified": item.lastModified,
            "Bitstreams": [],
        }
        if isinstance(item, DSpace6Item):  # Update after DSpace 8 migration
            bitstreams = item.bitstreams
        elif isinstance(item, DSpace8Item):
            bitstreams = self.client.get_bitstreams(bundle=bundle)
        else:
            raise TypeError("Item is neither a 'DSpace6Item' or a 'DSpace8Item'.")
        for bitstream in bitstreams:
            self.result_message["Bitstreams"].append(
                {
                    "BitstreamName": bitstream.name,
                    "BitstreamUUID": bitstream.uuid,
                    "BitstreamChecksum": bitstream.checkSum,
                }
            )

    def clean_up_partial_success_dspace6(self, item: DSpace6Item) -> None:
        logger.info("Item '%s' was partially posted to DSpace, cleaning up", item.handle)
        handle = item.handle
        for bitstream in item.bitstreams:
            if bitstream.uuid is not None:
                uuid = bitstream.uuid
                bitstream.delete(self.client)
                logger.info("Bitstream '%s' deleted from DSpace", uuid)
        item.delete(self.client)
        logger.info("Item '%s' deleted from DSpace", handle)

    def clean_up_partial_success_dspace8(self, item: DSpace8Item) -> None:
        handle = item.handle
        logger.info("Item '%s' was partially posted to DSpace, cleaning up", item.handle)
        try:
            self.client.delete_dso(item)
            logger.info("Item '%s' deleted from DSpace", handle)
        except Exception:
            logger.exception("Failed to delete DSpace item '%s'", handle)


def prettify(traceback: list) -> list[str]:
    output = []
    for item in traceback:
        lines = item.strip().split("\n")
        output.extend([line.strip().replace('\\"', "'") for line in lines])
    return output
