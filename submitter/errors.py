# submitter/errors.py
"""Submitter errors module.

This module includes custom Error classes that may be raised by the DSpace Submission
Service.
"""
import logging

from submitter import CONFIG

logger = logging.getLogger(__name__)


class ItemCreateError(Exception):
    """Exception raised when creating an item instance from a submission message.

    Args:
        metadata_file: Location of the metadata JSON file specified in the submission
            message

    Attributes:
        message (str): Explanation of the error

    """

    def __init__(self, metadata_file: str):
        self.message = (
            "Error occurred while creating item metadata entries from file "
            f"'{metadata_file}'"
        )


class ItemPostError(Exception):
    """Exception raised when posting an item to DSpace.

    Args:
        source_error: Originating Exception
        collection_handle: Collection to which the item was being posted

    Attributes:
        message (str): Explanation of the error
        dspace_error (str): Error message returned by the DSpace server
    """

    def __init__(self, source_error: Exception, collection_handle: str):
        self.message = (
            "Error occurred while posting item to DSpace collection "
            f"'{collection_handle}'"
        )
        self.dspace_error = source_error.response.text


class BitstreamAddError(Exception):
    """Exception raised when adding bitstream objects to an item instance.

    Attributes:
        message (str): Explanation of the error
    """

    def __init__(self):
        self.message = (
            "Error occurred while parsing bitstream information from files listed in "
            "submission message."
        )


class BitstreamOpenError(Exception):
    """Exception raised when opening a file to post as a bitstream to DSpace.

    Args:
        file_path: File path for bitstream being opened when error occurred
        item_handle: Handle of posted item that bitstream belongs to

    Attributes:
        message (str): Explanation of the error
    """

    def __init__(self, file_path: str, item_handle: str):
        self.message = (
            f"Error occurred while opening file '{file_path}' for bitstream. Item "
            f"'{item_handle}' and any bitstreams already posted to it will be deleted"
        )


class BitstreamPostError(Exception):
    """Exception raised when posting a bitstream to DSpace.

    Args:
        source_error: Originating Exception
        bitstream_name: Name of bitstream being posted when error occurred
        item_handle: Handle of posted item that bitstream belongs to

    Attributes:
        message (str): Explanation of the error
        dspace_error (str): Error message returned by the DSpace server
    """

    def __init__(self, source_error: Exception, bitstream_name: str, item_handle: str):
        self.message = (
            f"Error occurred while posting bitstream '{bitstream_name}' to item in "
            f"DSpace. Item '{item_handle}' and any bitstreams already posted to it "
            "will be deleted"
        )
        self.dspace_error = source_error.response.text


class DSpaceTimeoutError(Exception):
    """Exception raised due to a DSpace server timeout.

    Args:
        source_error: Originating Exception
        submission: Submission instance for which the error occurred

    Attributes:
        source_error(Exception): Originating exception
        message(str): Explanation of the error
    """

    def __init__(
        self,
        dspace_url: str,
        submission_attributes: dict,
    ):
        self.message = (
            f"DSpace server at '{dspace_url}' took more than {CONFIG.DSPACE_TIMEOUT} "
            "seconds to respond. Aborting DSpace Submission Service processing until "
            "this can be investigated.\nNOTE: The submission in process when this "
            "occurred likely has partially published data in DSpace. The package id "
            f"of the submission was '{submission_attributes['PackageID']}', from "
            f"source '{submission_attributes['SubmissionSource']}'"
        )


class SQSMessageSendError(Exception):
    """Exception raised when a message sent to an SQS result queue cannot be verified.

    Args:
        message_attributes: The attributes of the message that was not successfully sent
        message_body: The body of the message that was not succesfully sent
        result_queue: The name of the result queue that the message was sent to
        submit_message_id: The SQS ID of the corresponding submit message

    Attributes:
        message(str): Explanation of the error
    """

    def __init__(
        self,
        message_attributes: dict,
        message_body: dict,
        result_queue: str,
        submit_message_id: str,
    ):
        self.message = (
            f"Message was not successfully sent to result queue '{result_queue}', "
            "aborting DSpace Submission Service processing until this can be "
            "investigated. NOTE: The submit message is likely still in the submission "
            "queue and may need to be manually deleted before processing "
            f"resumes. Submit message ID: {submit_message_id}. Result message "
            f"attributes: {message_attributes}. Result message body: {message_body}"
        )


class SubmitMessageInvalidResultQueueError(Exception):
    """Exception raised due to an invalid result queue name in a submission message.

    Args:
        message_id: The SQS message ID of the message causing the error
        result_queue: The provided result queue name that caused the error

    Attributes:
        message(str): Explanation of the error
    """

    def __init__(self, message_id: str, result_queue: str):
        self.message = (
            "Aborting DSS processing due to a non-recoverable error:\nError occurred "
            f"while processing message '{message_id}' from input queue "
            f"'{CONFIG.INPUT_QUEUE}'. Message provided invalid result queue name "
            f"'{result_queue}'. Valid result queue names are: "
            f"{CONFIG.OUTPUT_QUEUES}."
        )


class SubmitMessageMissingAttributeError(Exception):
    """Exception raised due to a missing required attribute in a submission message.

    Args:
        message_id: The SQS message ID of the message causing the error
        attribute_name: The name of the attribute missing from the message

    Attributes:
        message(str): Explanation of the error
    """

    def __init__(self, message_id: str, attribute_name: str):
        self.message = (
            "Aborting DSS processing due to a non-recoverable error:\nError occurred "
            f"while processing message '{message_id}' from input queue "
            f"'{CONFIG.INPUT_QUEUE}'. Message was missing required attribute "
            f"'{attribute_name}'."
        )
