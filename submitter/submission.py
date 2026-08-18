import json
import logging
import os
import sys
import traceback
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

import requests
import smart_open
from dspace_rest_client.client import DSpaceClient
from dspace_rest_client.models import Bitstream, Bundle, Item

from submitter import errors
from submitter.config import Config
from submitter.message import validate_message

if TYPE_CHECKING:
    from mypy_boto3_sqs.service_resource import Message

logger = logging.getLogger(__name__)
CONFIG = Config()

# Shared cache for DSpace clients across all Submission instances
dspace_clients: dict[str, DSpaceClient] = {}


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
        self.client = self.get_dspace_client()
        logger.debug("Current clients in cache: %s", list(dspace_clients.keys()))

        try:
            item, bundle = self._submit_item()
            self.result_success_message(item, bundle)

        # Expected exception, generate error message and continue
        except errors.SubmissionError as exception:
            self.result_error_message(
                str(exception), getattr(exception, "dspace_error", None)
            )

        # DSpace timeout error, abort
        except requests.exceptions.Timeout as exception:
            dspace_url = self.client.base_url if self.client else "Unknown DSpace URL"
            raise errors.DSpaceTimeoutError(
                dspace_url, self.result_attributes
            ) from exception

        # Unexpected exception, abort
        except Exception:
            logger.exception(
                "Unexpected exception, aborting DSpace Submission Service processing"
            )
            raise

    def get_dspace_client(self) -> DSpaceClient:
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

    def _create_dspace_client(self, destination: str) -> DSpaceClient:
        """Create a DSpace client for the submission destination."""
        logger.debug(f"Creating DSpace client for destination '{destination}'")
        try:
            credentials = CONFIG.dspace_credentials[destination]
        except KeyError as exception:
            raise errors.InvalidDSpaceDestinationError(destination) from exception

        client = DSpaceClient(
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
        """Create a submission with all required data from a submission message.

        The SQS message is validated via two JSONSchema files, one for the message
        attributes and one for the message body.  If the message ATTRIBUTES fail
        validation, the job is killed immediately via the raised
        errors.SubmissionMessageBodyValidationError exception.  This bubbles up to
        the calling sqs.process() context because we cannot confidently remove the
        item from the input queue, which is because we cannot send an
        error result to the output queue.  By contrast, if only the message BODY
        fails validation, an error result is sent to the output queue,
        and the overall job continues.

        Args:
            message: An SQS message

        Raises:
            SubmissionMessageAttributesValidationError
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

    def _submit_item(self) -> tuple[Item, Bundle]:
        """Submit item instance from submission message.

        This method can handle either item 'create' or 'update' operations,
        which is indicated by self.operation. While this method raises a
        SubmissionError in the event of an invalid value for self.operation,
        if Submission is instantiated using from_message(), any invalid values
        would have been captured by JSON schema validation beforehand.
        """
        if self.operation == ValidItemOperations.UPDATE:
            try:
                item, bundle = self._update_item()
            except errors.SubmissionError:
                logger.exception(
                    f"Error occurred while updating item '{self.item_handle}'"
                )
                raise
        elif self.operation == ValidItemOperations.CREATE:
            try:
                item = self._create_item()
                bundle = self._create_bundle(item)
                for bitstream_uri in self.files or []:
                    self._create_bitstream(item, bundle, bitstream_uri)
            except errors.SubmissionError:
                logger.exception(
                    "Error occurred while creating item with PackageID="
                    f"{self.result_attributes.get('PackageID', {}).get('StringValue', 'unknown')}"  # noqa: E501
                )
                raise
        else:
            raise errors.SubmissionError(f"Operation not recognized: {self.operation}")
        return item, bundle

    def _create_item(self) -> Item:
        """Create item in DSpace from submission message.

        Note: Separate try-except blocks are added to distinguish any errors
        related to accessing and opening the file in S3 from errors related
        requests to the DSpace server. For the former, the exception is not
        passed to ItemError to avoid incorrect assignment to Submission.dspace_error.
        """
        # check whether the collection exists
        if self.collection_handle is None:
            raise errors.ItemError("collection_handle is required for item creation")

        collection = self.client.resolve_identifier_to_dso(
            identifier=self.collection_handle
        )
        if not collection:
            raise errors.DSpaceObjectNotFoundError(identifier=self.collection_handle)

        if self.metadata_location is None:
            raise errors.ItemError(
                message="metadata_location is required for item creation"
            )
        try:
            with smart_open.open(self.metadata_location, "r") as metadata:
                item_data = {
                    "metadata": json.load(metadata),
                    "discoverable": True,
                    "type": "item",
                }
        except Exception as exception:
            raise errors.ItemError(
                f"Failed to load metadata from {self.metadata_location}"
            ) from exception

        try:
            item = self.client.create_item(
                parent=collection.uuid,
                item=Item(item_data),
            )
        except Exception as exception:
            raise errors.ItemError(
                (
                    "Error occurred while creating item from file "
                    f"'{self.metadata_location}'"
                ),
                exception=exception,
            ) from exception

        # NOTE: This check is added to raise an exception when the returned
        # Item object's handle is None. Should be updated if/when dspace-rest-python
        # is updated to raise exceptions.
        if item.handle is None:
            raise errors.ItemError(
                f"Error occurred while creating item from file '{self.metadata_location}'"
            )

        logger.info(f"Item created with handle: {item.handle}")
        return item

    def _create_bundle(self, item: Item) -> Bundle:
        """Create ORIGINAL bundle for a specified item."""
        try:
            bundle = self.client.create_bundle(parent=item, name="ORIGINAL")
        except Exception as exception:
            self.clean_up_partial_success(item)
            raise errors.BundleError(
                (
                    f"Error occurred while creating bundle for item '{item.handle}' "
                    "in DSpace. Item and any bitstreams already posted to it will be deleted"  # noqa: E501
                ),
                exception=exception,
            ) from exception

        # NOTE: This check is added to raise an exception when the returned
        # Bundle object's uuid is None. Should be updated if/when dspace-rest-python
        # is updated to raise exceptions.
        if bundle.uuid is None:
            self.clean_up_partial_success(item)
            raise errors.BundleError(
                f"Error occurred while creating bundle for item '{item.handle}' "
                "in DSpace. Item and any bitstreams already posted to it will be deleted"
            )

        logger.info(f"Bundle created with UUID: {bundle.uuid}")
        return bundle

    def _create_bitstream(self, item: Item, bundle: Bundle, bitstream_data: dict) -> None:
        """Create bitstream for a specified item bundle."""
        try:
            bitstream = self.client.create_bitstream(
                bundle=bundle,
                name=os.path.basename(bitstream_data["BitstreamName"]),
                path=bitstream_data["FileLocation"],
            )
        except Exception as exception:
            self.clean_up_partial_success(item)
            raise errors.BitstreamError(
                (
                    "Error occurred while creating bitstream from file "
                    f"'{bitstream_data['BitstreamName']}' for item '{item.handle}'"
                ),
                exception=exception,
            ) from exception

        # NOTE: This check is added to raise an exception when the client
        # returns None. Should be updated if/when dspace-rest-python
        # is updated to raise exceptions.
        if bitstream is None:
            self.clean_up_partial_success(item)
            raise errors.BitstreamError(
                (
                    "Error occurred while creating bitstream from file "
                    f"'{bitstream_data['BitstreamName']}' for item '{item.handle}'"
                ),
            )

        logger.info(f"Bitstream created with UUID: {bitstream.uuid}")

    def _update_item(self) -> tuple[Item, Bundle]:
        """Update item in DSpace"""
        if not self.item_handle:
            raise errors.ItemError(
                "The 'item_handle' attribute must be a non-empty string"
            )

        dspace_object = self.client.resolve_identifier_to_dso(identifier=self.item_handle)
        if not dspace_object:
            raise errors.DSpaceObjectNotFoundError(self.item_handle)
        item = Item(dso=dspace_object)  # need to cast to Item

        logger.debug(
            "At this time, the 'update' operation only updates bitstreams "
            "and adding metadata fields related to bitstream update!"
        )
        bundle = self._update_item_bitstream(item)
        return item, bundle

    def _update_item_bitstream(self, item: Item) -> Bundle:
        """Update bitstreams for an item in DSpace.

        This method performs a full replacement of an item's bitstreams, which
        are stored in the item's 'ORIGINAL' bundle. A full replacement means
        old, pre-existing bitstreams are deleted from the bundle.

        NOTE: At this time, DSS will only update items with a single bitstream
        in their 'ORIGINAL' bundle.
        """
        # get update date and timestamp
        time = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        old_bitstream, bundle = self._get_item_bitstream_bundle(item)
        new_bitstreams = self._upload_new_item_bitstreams(item, bundle)

        # add metadata entry for successfully added bitstreams
        self.client.add_metadata(
            item,
            field="dc.description.provenance",
            value=(
                f"Updated bitstreams on {time}: "
                f"{[bitstream.name for bitstream in new_bitstreams]}"
            ),
        )

        # delete original bitstream
        # add metadata entry for deleted bitstream
        if old_bitstream is not None:
            self._delete_old_item_bitstream(item, old_bitstream)
            self.client.add_metadata(
                item,
                field="dc.description.provenance",
                value=(f"Deleted bitstream on {time}: {old_bitstream.name}"),
            )

        return bundle

    def _get_original_bundle(self, item: Item) -> Bundle:
        for bundle in self.client.get_bundles_iter(parent=item):
            if bundle.name == "ORIGINAL":
                return bundle
        raise errors.ItemError(f"Item {item.handle} does not have an 'ORIGINAL' bundle")

    def _get_item_bitstream_bundle(self, item: Item) -> tuple[Bitstream | None, Bundle]:
        """Retrieve single bitstream from an item's 'ORIGINAL' bundle."""
        bundle = self._get_original_bundle(item)
        bitstreams = self.client.get_bitstreams(bundle=bundle)

        if len(bitstreams) > 1:
            raise errors.ItemError(
                f"The 'ORIGINAL' bundle {bundle.uuid} for item '{item.handle}' "
                f"contains {len(bitstreams)} bitstreams"
            )
        if len(bitstreams) == 0:
            logger.warning(
                f"'ORIGINAL' bundle {bundle.uuid} for item '{item.handle}' is empty"
            )
            return None, bundle

        return bitstreams[0], bundle

    def _upload_new_item_bitstreams(self, item: Item, bundle: Bundle) -> list[Bitstream]:
        """Upload new bitstreams to item bundle.

        The method will attempt to upload all the bitstreams specified in
        `Submission.files` and track any failing bitstreams in a list. If any
        new bitstreams fail upload, the method will undo all successful bitstream
        uploads and raise a `BitstreamError` that optionally includes a message
        indicating whether the original item state was restored. Otherwise,
        the method returns a list of the newly added bitstreams.
        """
        if not self.files:
            raise errors.ItemError("The 'files' attribute cannot be empty")

        added_bitstreams: list[Bitstream] = []
        failed_bitstreams: list[str] = []

        # update 'ORIGINAL' bundle with new bitstreams
        for bitstream_uri in self.files:
            try:
                bitstream = self.client.create_bitstream(
                    bundle=bundle,
                    name=os.path.basename(bitstream_uri["BitstreamName"]),
                    path=bitstream_uri["FileLocation"],
                )
            except Exception:  # noqa: BLE001
                failed_bitstreams.append(bitstream_uri["BitstreamName"])
                continue
            else:
                # NOTE: This check is added because the client can return None
                if bitstream is None:
                    failed_bitstreams.append(bitstream_uri["BitstreamName"])
                else:
                    added_bitstreams.append(bitstream)

        if failed_bitstreams:
            if not added_bitstreams:
                raise errors.BitstreamError(
                    (
                        f"Error occurred while creating bitstream(s) for item {item.handle} "  # noqa: E501
                        f"with the following files: {failed_bitstreams}; "
                    ),
                )
            remaining_bitstreams = self._undo_bitstream_updates(added_bitstreams)
            if len(remaining_bitstreams) > 0:
                raise errors.BitstreamError(
                    (
                        f"Error occurred while creating bitstream(s) for item {item.handle} "  # noqa: E501
                        f"with the following files: {failed_bitstreams}; "
                        "failed to restore item to original state. "
                        "Please delete the following bitstreams to restore item state: "
                        f"{remaining_bitstreams}"
                    ),
                )
            raise errors.BitstreamError(
                (
                    f"Error occurred while creating bitstream(s) for item {item.handle} "
                    f"with the following files: {failed_bitstreams}; "
                    "restored item to original state."
                ),
            )

        return added_bitstreams

    def _delete_old_item_bitstream(self, item: Item, bitstream: Bitstream) -> None:
        try:
            self._delete_bitstream(bitstream)
        except errors.BitstreamError as exception:
            raise errors.BitstreamError(
                f"Error occurred while deleting original bitstream "
                f"'{bitstream.name}' for item '{item.handle}'. "
                f"Please delete this file to complete item update."
            ) from exception

    def _undo_bitstream_updates(self, bitstreams: list[Bitstream]) -> list[Bitstream]:
        """Delete bitstreams according to a provided list.

        Call this method to restore the item's original state if any bitstream
        uploads fail during an item update. The purpose is to remove
        all bitstreams uploaded during a failed item update, restoring the item
        to its state before the update was attempted.

        Returns a list of bitstreams that could not be deleted. An empty list
        indicates the item was fully restored to its original state.
        """
        if not bitstreams:
            logger.info("'bitstreams' is empty, nothing to delete!")
            return []

        deleted_bitstreams: list[Bitstream] = []
        for bitstream in bitstreams:
            try:
                self._delete_bitstream(bitstream)
                deleted_bitstreams.append(bitstream)
            except errors.BitstreamError:
                logger.exception("Error occurred while undoing bitstream update")

        return list(set(bitstreams) - set(deleted_bitstreams))

    def _delete_bitstream(self, bitstream: Bitstream) -> None:
        """Delete Bitstream object.

        NOTE: This code was pulled from dspace-rest-python's (v0.1.17)
        client.delete_dso method. The client.delete_dso method only supports
        deletion of SimpleDSpaceObject's,  which does not include the Bitstream object.
        This is a temporary workaround until the client is updated or we find an
        alternative way to send requests to DSpace REST API.
        """
        try:
            bitstream_url = bitstream.links["self"]["href"]
            response = self.client.api_delete(url=bitstream_url, params=None)
        except ValueError as exception:
            raise errors.BitstreamError(
                f"Error occurred while deleting bitstream {bitstream.uuid}",
                exception=exception,
            ) from exception

        # NOTE: This check is added to raise an exception if
        # response.status_code is not equal to 204 (No Content).
        # Should be updated if/when dspace-rest-python is
        # updated to raise exceptions.
        if response.status_code != 204:  # noqa: PLR2004
            raise errors.BitstreamError(
                f"Error occurred while deleting bitstream {bitstream.uuid}: "
                f"{response.status_code} {response.text}"
            )

        logger.info(
            f"Bitstream '{bitstream.name}' (uuid={bitstream.uuid}) deleted from DSpace"
        )

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

    def result_success_message(self, item: Item, bundle: Bundle) -> None:
        """Set result message on Submission object on successful submit."""
        self.result_message = {
            "ResultType": "success",
            "ItemHandle": item.handle,
            "lastModified": item.lastModified,
            "Bitstreams": [],
        }

        bitstreams = self.client.get_bitstreams(bundle=bundle)

        for bitstream in bitstreams:
            self.result_message["Bitstreams"].append(
                {
                    "BitstreamName": bitstream.name,
                    "BitstreamUUID": bitstream.uuid,
                    "BitstreamChecksum": bitstream.checkSum,
                }
            )

    def clean_up_partial_success(self, item: Item) -> None:
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
