import logging

import click

from submitter import config
from submitter.sample_data import sample_data
from submitter.sqs import message_loop

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
    "--queue",
    default=config.INPUT_QUEUE,
    help="Name of queue to load sample messages to",
)
def sample_data_loader(queue):
    logger.info("sample this!")
    sample_data(queue)
    logger.info("sample data (probably) loaded into input queue")
