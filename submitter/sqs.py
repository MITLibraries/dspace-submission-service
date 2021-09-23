import json
import logging

import boto3
from dspace.client import DSpaceClient

from submitter import config
from submitter.submission import Submission

logger = logging.getLogger(__name__)


def message_loop(queue, wait):
    logger.info("Message loop started")
    msgs = retrieve_messages_from_queue(queue, wait)

    if len(msgs) > 0:
        process(msgs)
        message_loop(queue, wait)
    else:
        logger.info("No messages available in queue %s", queue)


def process(msgs):
    client = DSpaceClient(config.DSPACE_API_URL)
    client.login(config.DSPACE_USER, config.DSPACE_PASSWORD)

    for message in msgs:
        message_id = message.message_attributes["PackageID"]["StringValue"]
        message_source = message.message_attributes["SubmissionSource"]["StringValue"]
        logger.info("Processing message %s from source %s", message_id, message_source)
        try:
            submission = Submission.from_message(message)
        except Exception as e:
            # TODO: handle and test submit message errors
            raise e
        submission.submit(client)
        write_message_to_queue(
            submission.result_attributes,
            json.dumps(submission.result_message),
            submission.result_queue,
        )
        # TODO: probs better to confirm the write to the output was good
        # before cleanup but for now yolo it
        message.delete()
        logger.info("Deleted message %s from input queue", message_id)


def retrieve_messages_from_queue(input_queue, wait):
    sqs = boto3.resource("sqs")
    queue = sqs.get_queue_by_name(QueueName=input_queue)

    logger.info("Polling queue %s for messages", input_queue)
    msgs = queue.receive_messages(
        MaxNumberOfMessages=10,
        WaitTimeSeconds=wait,
        MessageAttributeNames=["All"],
        AttributeNames=["All"],
    )
    logger.info("%d messages received", len(msgs))

    return msgs


def write_message_to_queue(attributes, body, output_queue):
    sqs = boto3.resource("sqs")
    queue = sqs.get_queue_by_name(QueueName=output_queue)
    queue.send_message(
        MessageAttributes=attributes,
        MessageBody=body,
    )
    logger.info("Wrote message to %s with message body: %s", output_queue, body)
