import hashlib
import json
import logging
from typing import TYPE_CHECKING

import boto3

from submitter import errors
from submitter.config import Config
from submitter.submission import Submission

if TYPE_CHECKING:
    from mypy_boto3_sqs.service_resource import Message, Queue, SQSServiceResource
    from mypy_boto3_sqs.type_defs import SendMessageResultTypeDef

logger = logging.getLogger(__name__)
CONFIG = Config()

# Cache for SQS queues
_sqs_queues: dict[str, "Queue"] = {}


def sqs_client() -> "SQSServiceResource":
    return boto3.resource(
        service_name="sqs",
        endpoint_url=CONFIG.sqs_endpoint_url,
    )


def _get_sqs_queue(queue_name: str) -> "Queue":
    """Get SQS queue, retrieving from cache if available."""
    if queue_name not in _sqs_queues:
        _sqs_queues[queue_name] = sqs_client().get_queue_by_name(QueueName=queue_name)
    return _sqs_queues[queue_name]


def message_loop(queue: str, wait: int, visibility: int = 30) -> None:
    logger.info("Message loop started")
    while True:
        msgs = retrieve_messages_from_queue(queue, wait, visibility)
        if not msgs:
            logger.info("No messages available in queue %s", queue)
            break
        process(msgs)


def process(msgs: list["Message"]) -> None:

    for message in msgs:
        message_id = message.message_id
        logger.info(
            "Processing message '%s' from queue '%s'", message_id, CONFIG.input_queue
        )

        if CONFIG.skip_processing:
            logger.info("Skipping processing due to config")
        else:
            submission = Submission.from_message(message)
            if not submission.result_message:
                submission.submit()
            response = write_message_to_queue(
                submission.result_attributes,
                submission.result_message,
                submission.result_queue,
            )
            if not verify_sent_message(submission.result_message, response):
                raise errors.SQSMessageSendError(
                    submission.result_attributes,
                    submission.result_message,
                    submission.result_queue,
                    response["MessageId"],
                )
            logger.debug(
                "Wrote message to queue '%s' with message body: %s",
                submission.result_queue,
                json.dumps(submission.result_message),
            )
        message.delete()
        logger.info("Deleted message '%s' from input queue", message_id)


def retrieve_messages_from_queue(
    input_queue: str,
    wait: int,
    visibility: int = 30,
) -> list["Message"]:
    queue = _get_sqs_queue(input_queue)

    logger.info("Polling queue %s for messages", input_queue)
    msgs = queue.receive_messages(
        MaxNumberOfMessages=10,
        WaitTimeSeconds=wait,
        MessageAttributeNames=["All"],
        AttributeNames=["All"],
        VisibilityTimeout=visibility,
    )
    logger.info("%d messages received", len(msgs))

    return msgs


def write_message_to_queue(
    attributes: dict,
    body: dict | str | None,
    output_queue: str,
) -> "SendMessageResultTypeDef":
    queue = _get_sqs_queue(output_queue)
    return queue.send_message(
        MessageAttributes=attributes,
        MessageBody=json.dumps(body),
    )


def create(name: str) -> "Queue":
    sqs = sqs_client()
    return sqs.create_queue(QueueName=name)


def verify_sent_message(
    sent_message_body: dict | str | None,
    sqs_send_message_response: "SendMessageResultTypeDef",
) -> bool:
    body_md5 = hashlib.md5(  # nosec # noqa: S324
        json.dumps(sent_message_body).encode("utf-8")
    ).hexdigest()
    return body_md5 == sqs_send_message_response["MD5OfMessageBody"]
