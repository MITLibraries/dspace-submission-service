# submitter/errors.py
"""Submitter errors module.

This module includes custom Error classes that may be raised by the DSpace Submission
Service.
"""

import logging

from requests.exceptions import RequestException

from submitter.config import Config

logger = logging.getLogger(__name__)
CONFIG = Config()


class InvalidDSpaceDestinationError(Exception):
    """Exception raised when an invalid DSpace destination is specified.

    Args:
        destination: The invalid destination name
    Attributes:
        message (str): Explanation of the error
    """

    def __init__(self, destination: str | None):
        message = f"Invalid DSpace destination specified: '{destination}'."
        super().__init__(message)


class SubmissionError(Exception):
    def __init__(self, message: str, exception: Exception | None = None):
        super().__init__(message)
        self.exception = exception

        if (
            isinstance(self.exception, RequestException)
            and self.exception.response is not None
        ):
            self.dspace_error = self.exception.response.text


class DSpaceObjectNotFoundError(SubmissionError):
    """Exception raised when identifier was not resolved to a DSpace object.

    The client for DSpace 8 will return None if it either did not find any objects
    associated with the identifier, which should be a handle or DOI, or
    the identifier was not resolvable.

    https://github.com/DSpace/RestContract/blob/main/identifiers.md#find-dso-by-identifier-endpoint
    """

    def __init__(self, identifier: str):
        message = f"Did not find any DSpace objects associated with the identifier: '{identifier}'"  # noqa: E501
        super(SubmissionError, self).__init__(message)


class ItemError(SubmissionError):
    """Exception raised when creating or updating an item in DSpace.

    This exception is used in the following cases:
        - The DSpace client will returns an Item object without an item handle

    Args:
        exception: The exception raised during item creation

    Attributes:
        message (str): Explanation of the error
        dspace_error (str): Error message returned by the DSpace server, if applicable
    """


class BundleError(SubmissionError):
    """Exception raised when creating a bundle for an item in DSpace.

    Args:
        exception: The exception raised during bundle creation

    Attributes:
        message (str): Explanation of the error
        dspace_error (str): Error message returned by the DSpace server, if applicable
    """


class BitstreamError(SubmissionError):
    """Exception raised when creating a bitstream instance from a submission message.

    Args:
        exception: The exception raised during bitstream creation

    Attributes:
        message (str): Explanation of the error
        dspace_error (str): Error message returned by the DSpace server, if applicable
    """


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
        message = (
            f"DSpace server at '{dspace_url}' took more than {CONFIG.dspace_timeout} "
            "seconds to respond. Aborting DSpace Submission Service processing until "
            "this can be investigated.\nNOTE: The submission in process when this "
            "occurred likely has partially published data in DSpace. The package id "
            f"of the submission was '{submission_attributes['PackageID']}', from "
            f"source '{submission_attributes['SubmissionSource']}'"
        )
        super().__init__(message)


class DSpaceAuthenticationError(Exception):
    """Exception raised due to a failure to authenticate to the DSpace server.

    Args:
        source_error: Originating Exception
        dspace_url: The URL of the DSpace server to which authentication was attempted

    Attributes:
        source_error(Exception): Originating exception
        message(str): Explanation of the error
    """

    def __init__(
        self,
        dspace_url: str | float | None,
        dspace_user: str | float | None,
    ):
        message = (
            f"Failed to authenticate to DSpace server at '{dspace_url}' with user "
            f"'{dspace_user}'. Please verify that the DSS_DSPACE_CREDENTIALS "
            "environment variable is set correctly and that the DSpace server is "
            "accessible."
        )
        super().__init__(message)


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
        message_body: dict | str | None,
        result_queue: str,
        submit_message_id: str,
    ):
        message = (
            f"Message was not successfully sent to result queue '{result_queue}', "
            "aborting DSpace Submission Service processing until this can be "
            "investigated. NOTE: The submit message is likely still in the submission "
            "queue and may need to be manually deleted before processing "
            f"resumes. Submit message ID: {submit_message_id}. Result message "
            f"attributes: {message_attributes}. Result message body: {message_body}"
        )
        super().__init__(message)


# Submission message validation errors
class SubmissionMessageAttributesValidationError(Exception):
    """Exception raised due when submission message attributes are invalid"""


class SubmissionMessageBodyValidationError(Exception):
    """Exception raised due when submission message body is invalid"""
