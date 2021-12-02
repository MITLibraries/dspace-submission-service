import json
import logging

import boto3
from dspace.client import DSpaceClient

from submitter import CONFIG
from submitter.submission import Submission

logger = logging.getLogger(__name__)


def sqs_client():
    sqs = boto3.resource(
        service_name="sqs",
        region_name=CONFIG.AWS_REGION_NAME,
        endpoint_url=CONFIG.SQS_ENDPOINT_URL,
    )

    return sqs


def message_loop(queue, wait, visibility=30):
    logger.info("Message loop started")
    msgs = retrieve_messages_from_queue(queue, wait, visibility)

    if len(msgs) > 0:
        process(msgs)
        message_loop(queue, wait)
    else:
        logger.info("No messages available in queue %s", queue)


def process(msgs):
    if CONFIG.SKIP_PROCESSING != "true":
        client = DSpaceClient(CONFIG.DSPACE_API_URL, timeout=CONFIG.DSPACE_TIMEOUT)
        client.login(CONFIG.DSPACE_USER, CONFIG.DSPACE_PASSWORD)

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
                submission.submit(client)
            write_message_to_queue(
                submission.result_attributes,
                submission.result_message,
                submission.result_queue,
            )
        # TODO: probs better to confirm the write to the output was good
        # before cleanup but for now yolo it
        message.delete()
        logger.info("Deleted message '%s' from input queue", message_id)


def retrieve_messages_from_queue(input_queue, wait, visibility=30):
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


def write_message_to_queue(attributes: dict, body: dict, output_queue: str):
    sqs = sqs_client()
    queue = sqs.get_queue_by_name(QueueName=output_queue)
    queue.send_message(
        MessageAttributes=attributes,
        MessageBody=json.dumps(body),
    )
    logger.debug(
        "Wrote message to queue '%s' with message body: %s",
        output_queue,
        json.dumps(body, indent=2),
    )


def create(name):
    sqs = sqs_client()
    queue = sqs.create_queue(QueueName=name)
    return queue
