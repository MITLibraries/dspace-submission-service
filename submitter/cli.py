import logging

import click

from submitter import config
from submitter.sample_data import sample_data
from submitter.sqs import create, message_loop

logger = logging.getLogger(__name__)


@click.group()
def main():
    pass


@main.command()
@click.option(
    "--queue", default=config.INPUT_QUEUE, help="Name of queue to process messages from"
)
@click.option("--wait", default=20, help="seconds to wait for long polling. max 20")
def start(queue, wait):
    logger.info("Starting processing messages from queue %s", queue)
    message_loop(queue, wait)
    logger.info("Completed processing messages from queue %s", queue)


@main.command()
@click.option(
    "--input_queue",
    default=config.INPUT_QUEUE,
    help="Name of queue to load sample messages to",
)
@click.option(
    "--output_queue",
    help="Name of queue to send output messages to",
)
def sample_data_loader(input_queue, output_queue):
    logger.info("sample this!")
    sample_data(input_queue, output_queue)
    logger.info("sample data (probably) loaded into input queue")


@main.command()
@click.option("--name", help="name of queue to create")
def create_queue(name):
    queue = create(name)
    logger.info(queue.url)
