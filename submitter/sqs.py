import hashlib
import json
import logging
from typing import TYPE_CHECKING

import boto3

from submitter import CONFIG, errors
from submitter.submission import Submission

if TYPE_CHECKING:
    from mypy_boto3_sqs.service_resource import Message, Queue, SQSServiceResource
    from mypy_boto3_sqs.type_defs import SendMessageResultTypeDef

logger = logging.getLogger(__name__)


def sqs_client() -> "SQSServiceResource":
    return boto3.resource(
        service_name="sqs",
        region_name=CONFIG.AWS_REGION_NAME,
        endpoint_url=CONFIG.SQS_ENDPOINT_URL,
    )


def message_loop(queue: str, wait: int, visibility: int = 30) -> None:
    logger.info("Message loop started")
    msgs = retrieve_messages_from_queue(queue, wait, visibility)

    if len(msgs) > 0:
        process(msgs)
        message_loop(queue, wait)
    else:
        logger.info("No messages available in queue %s", queue)


def process(msgs: list["Message"]) -> None:

    for message in msgs:
        message_id = message.message_id
        logger.info(
            "Processing message '%s' from queue '%s'", message_id, CONFIG.INPUT_QUEUE
        )

        if CONFIG.SKIP_PROCESSING == "true":
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
    sqs = sqs_client()
    queue = sqs.get_queue_by_name(QueueName=input_queue)

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
    sqs = sqs_client()
    queue = sqs.get_queue_by_name(QueueName=output_queue)
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
