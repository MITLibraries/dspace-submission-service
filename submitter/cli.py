import logging

import click

from submitter.config import Config, configure_logger, configure_sentry
from submitter.errors import DSpaceAuthenticationError
from submitter.message import (
    generate_result_messages_from_file,
    generate_submission_messages_from_file,
)
from submitter.sqs import create, message_loop, write_message_to_queue
from submitter.submission import Submission

logger = logging.getLogger(__name__)
CONFIG = Config()


@click.group()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    required=False,
    help="Flag for verbose output.",
)
def main(*, verbose: bool) -> None:
    root_logger = logging.getLogger()
    logger.info(
        configure_logger(
            root_logger=root_logger,
            verbose=verbose,
            warning_only_loggers=CONFIG.warning_only_loggers,
        )
    )
    configure_sentry()


@main.command()
@click.option(
    "--queue", envvar="INPUT_QUEUE", help="Name of queue to process messages from"
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
    envvar="INPUT_QUEUE",
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
@click.option(
    "--submission-system",
    required=True,
    help="Name of submission system to verify connection to",
)
def verify_dspace_connection(
    submission_system: str,
) -> None:
    submission = Submission(
        destination=submission_system,
        attributes={},
        result_queue="non_existent_queue",
    )
    credentials = CONFIG.dspace_credentials[submission_system]
    try:
        submission.get_dspace_client()
    except DSpaceAuthenticationError:
        logger.exception(
            f'Failed to authenticate to "{credentials["url"]}" as '
            f'"{credentials["user"]}"',
        )
    else:
        logger.info(
            f'Successfully authenticated to "{credentials["url"]}" as '
            f'"{credentials["user"]}"',
        )
