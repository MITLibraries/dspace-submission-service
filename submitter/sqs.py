import json
import logging

import boto3
from dspace.client import DSpaceClient

from submitter import config
from submitter.submission import Submission

logger = logging.getLogger(__name__)


def sqs_client():
    sqs = boto3.resource(
        service_name="sqs",
        region_name=config.AWS_REGION_NAME,
        endpoint_url=config.SQS_ENDPOINT_URL,
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
    if config.SKIP_PROCESSING != "true":
        client = DSpaceClient(config.DSPACE_API_URL, timeout=config.DSPACE_TIMEOUT)
        client.login(config.DSPACE_USER, config.DSPACE_PASSWORD)

    for message in msgs:
        message_id = message.message_attributes["PackageID"]["StringValue"]
        message_source = message.message_attributes["SubmissionSource"]["StringValue"]
        logger.info("Processing message %s from source %s", message_id, message_source)

        if config.SKIP_PROCESSING == "true":
            logger.info("Skipping processing due to config")
        else:
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


def write_message_to_queue(attributes, body, output_queue):
    sqs = sqs_client()
    queue = sqs.get_queue_by_name(QueueName=output_queue)
    queue.send_message(
        MessageAttributes=attributes,
        MessageBody=body,
    )
    logger.info("Wrote message to %s with message body: %s", output_queue, body)


def create(name):
    sqs = sqs_client()
    queue = sqs.create_queue(QueueName=name)
    return queue


def data_loader(
    id, source, target, col_hdl, meta_loc, filename, fileloc, input_queue, output_queue
):
    sqs = sqs_client()
    queue = sqs.get_queue_by_name(QueueName=input_queue)
    body = {
        "SubmissionSystem": target,
        "CollectionHandle": col_hdl,
        "MetadataLocation": meta_loc,
        "Files": [
            {"BitstreamName": filename, "FileLocation": fileloc},
        ],
    }
    # Send message to SQS queue
    queue.send_message(
        MessageAttributes={
            "PackageID": {"DataType": "String", "StringValue": id},
            "SubmissionSource": {"DataType": "String", "StringValue": source},
            "OutputQueue": {"DataType": "String", "StringValue": output_queue},
        },
        MessageBody=(json.dumps(body)),
    )
