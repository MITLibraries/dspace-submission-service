import logging

import click

from submitter import CONFIG
from submitter.message import (
    generate_result_messages_from_file,
    generate_submission_messages_from_file,
)
from submitter.s3 import check_s3_permissions
from submitter.sqs import (
    check_read_permissions,
    check_write_permissions,
    create,
    message_loop,
    write_message_to_queue,
)
from submitter.ssm import SSM

logger = logging.getLogger(__name__)


@click.group()
def main():
    pass


@main.command()
@click.option(
    "--queue", default=CONFIG.INPUT_QUEUE, help="Name of queue to process messages from"
)
@click.option("--wait", default=20, help="seconds to wait for long polling. max 20")
def start(queue, wait):
    logger.info("Starting processing messages from queue %s", queue)
    message_loop(queue, wait)
    logger.info("Completed processing messages from queue %s", queue)


@main.command()
@click.option(
    "-i",
    "--input-queue",
    default=CONFIG.INPUT_QUEUE,
    help="Name of queue to load sample messages to",
)
@click.option(
    "-o",
    "--output-queue",
    required=True,
    help="Name of output queue to send result messages to",
)
@click.option(
    "-f",
    "--filepath",
    type=click.Path(exists=True),
    default="tests/fixtures/completely-fake-data.json",
    help="Path to json file of sample messages to load",
)
def load_sample_input_data(input_queue, output_queue, filepath):
    logger.info(f"Loading sample data from file '{filepath}' into queue {input_queue}")
    count = 0
    messages = generate_submission_messages_from_file(filepath, output_queue)
    for message in messages:
        write_message_to_queue(message[0], message[1], input_queue)
        count += 1
    logger.info(f"{count} messages loaded into queue {input_queue}")


@main.command()
@click.option(
    "-o",
    "--output-queue",
    help="Name of queue to load sample messages to",
)
@click.option(
    "-f",
    "--filepath",
    type=click.Path(exists=True),
    default="tests/fixtures/completely-fake-data.json",
    help="Path to json file of sample messages to load",
)
def load_sample_output_data(output_queue, filepath):
    logger.info(f"Loading sample data from file '{filepath}' into queue {output_queue}")
    count = 0
    messages = generate_result_messages_from_file(filepath, output_queue)
    for message in messages:
        write_message_to_queue(message[0], message[1], output_queue)
        count += 1
    logger.info(f"{count} messages loaded into queue {output_queue}")


@main.command()
@click.argument("name")
def create_queue(name):
    """Create queue with NAME supplied as argument"""
    queue = create(name)
    logger.info(queue.url)


@main.command()
def check_permissions():
    """Confirm DSS infrastructure has deployed properly with correct permissions to all
    expected resources given the current env configuration.

    Note: Only useful in stage and prod envs, as this command requires SSM access which
        does not get configured in dev.

    Note: Checking SQS write permissions does write a message to each configured output
        queue. The test message gets deleted as part of the process, however if there
        are already more than 10 messages in the output queue that delete may not
        happen and the test message will remain in the queue. It is best to only run
        this command when the configured output queues are empty.
    """

    # Confirm we can retrieve an encrypted ssm parameter
    ssm = SSM()
    logger.info(ssm.check_permissions(CONFIG.SSM_PATH))

    # Confirm we can read from and write to all expected SQS queues
    logger.info(check_read_permissions(CONFIG.INPUT_QUEUE))
    for queue in CONFIG.VALID_RESULT_QUEUES:
        logger.info(check_write_permissions(queue))

    # Confirm we can list and get objects from all expected s3 buckets
    logger.info(check_s3_permissions(CONFIG.S3_BUCKETS))

    logger.info(f"All permissions confirmed for env '{CONFIG.ENV}'")
