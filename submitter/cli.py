import logging

import click
from dspace.client import DSpaceClient
from requests.exceptions import HTTPError

from submitter import CONFIG
from submitter.message import (
    generate_result_messages_from_file,
    generate_submission_messages_from_file,
)
from submitter.sqs import create, message_loop, write_message_to_queue

logger = logging.getLogger(__name__)


@click.group()
def main() -> None:
    pass


@main.command()
@click.option(
    "--queue", default=CONFIG.INPUT_QUEUE, help="Name of queue to process messages from"
)
@click.option("--wait", default=20, help="seconds to wait for long polling. max 20")
def start(queue: str, wait: int) -> None:
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
def load_sample_input_data(input_queue: str, output_queue: str, filepath: str) -> None:
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
def load_sample_output_data(output_queue: str, filepath: str) -> None:
    logger.info(f"Loading sample data from file '{filepath}' into queue {output_queue}")
    count = 0
    messages = generate_result_messages_from_file(filepath, output_queue)
    for message in messages:
        write_message_to_queue(message[0], message[1], output_queue)
        count += 1
    logger.info(f"{count} messages loaded into queue {output_queue}")


@main.command()
@click.argument("name")
def create_queue(name: str) -> None:
    """Create queue with NAME supplied as argument"""
    queue = create(name)
    logger.info(queue.url)


@main.command()
def verify_dspace_connection() -> None:
    client = DSpaceClient(CONFIG.DSPACE_API_URL, timeout=CONFIG.DSPACE_TIMEOUT)
    try:
        client.login(CONFIG.DSPACE_USER, CONFIG.DSPACE_PASSWORD)
    except HTTPError:
        logger.exception(
            "Failed to authenticate to %s as %s",
            CONFIG.DSPACE_API_URL,
            CONFIG.DSPACE_USER,
        )
    else:
        logger.info(
            "Successfully authenticated to %s as %s",
            CONFIG.DSPACE_API_URL,
            CONFIG.DSPACE_USER,
        )
