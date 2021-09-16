import json
import logging
import traceback
from datetime import datetime

import dspace
import smart_open

logger = logging.getLogger(__name__)


class Submission:
    def __init__(
        self,
        destination,
        collection_handle,
        metadata_location,
        files,
        attributes,
        result_queue,
    ):
        self.destination = destination
        self.collection_handle = collection_handle
        self.metadata_location = metadata_location
        self.files = files
        self.result_attributes = attributes
        self.result_message = None
        self.result_queue = result_queue

    @classmethod
    def from_message(cls, message):
        body = json.loads(message.body)
        return cls(
            destination=body["SubmissionSystem"],
            collection_handle=body["CollectionHandle"],
            metadata_location=body["MetadataLocation"],
            files=body["Files"],
            attributes={
                "PackageID": message.message_attributes["PackageID"],
                "SubmissionSource": message.message_attributes["SubmissionSource"],
            },
            result_queue=message.message_attributes["OutputQueue"]["StringValue"],
        )

    def get_metadata_entries_from_file(self):
        with smart_open.open(self.metadata_location) as f:
            metadata = json.load(f)
            for entry in metadata["metadata"]:
                yield entry

    def result_error_message(self, error, info):
        time = datetime.now()
        self.result_message = {
            "ResultType": "error",
            "ErrorTimestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ErrorInfo": info,
            "ExceptionMessage": str(error),
            "ExceptionTraceback": traceback.format_exc(),
        }

    def result_success_message(self, item):
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

    def submit(self, client):
        # Create item instance and add metadata
        try:
            item = dspace.item.Item()
            for entry in self.get_metadata_entries_from_file():
                metadata_entry = dspace.item.MetadataEntry.from_dict(entry)
                item.metadata.append(metadata_entry)
        except Exception as e:
            self.result_error_message(
                e, "Error occurred while creating item metadata from file"
            )
            return

        # Add bitstreams to item from files
        logger.info("Adding bitstreams to item")
        try:
            for file in self.files:
                bitstream = dspace.bitstream.Bitstream(
                    file_path=file["FileLocation"],
                    name=file["BitstreamName"],
                    description=file.get("BitstreamDescription"),
                )
                item.bitstreams.append(bitstream)
        except Exception as e:
            self.result_error_message(
                e, "Error occurred while adding bitstreams to item from files"
            )
            return

        # Post item to DSpace
        try:
            item.post(client, collection_handle=self.collection_handle)
        except Exception as e:
            self.result_error_message(e, "Error occurred while posting item to DSpace")
            return
        logger.info("Posted item to Dspace with handle %s", item.handle)

        # Post all bitstreams to item
        try:
            for bitstream in item.bitstreams:
                bitstream.post(client, item_uuid=item.uuid)
        except Exception as e:
            handle = item.handle
            for bitstream in item.bitstreams:
                if bitstream.uuid is not None:
                    bitstream.delete(client)
            item.delete(client)
            self.result_error_message(
                e,
                (
                    f"Error occurred while posting bitstreams to item in DSpace. Item "
                    f"with handle {handle} and any successfully posted bitstreams "
                    f"have been deleted"
                ),
            )
            return
        logger.info(
            "Posted %d bitstreams to item with handle %s",
            len(item.bitstreams),
            item.handle,
        )
        self.result_success_message(item)
