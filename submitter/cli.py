import click

from submitter import INPUT_QUEUE, OUTPUT_QUEUE
from submitter.sample_data import sample_data
from submitter.sqs import message_loop


@click.group()
def main():
    pass


@main.command()
@click.option(
    "--input-queue", default=INPUT_QUEUE, help="queue name to use as input queue"
)
@click.option(
    "--output-queue", default=OUTPUT_QUEUE, help="queue name to use as output queue"
)
@click.option("--wait", default=20, help="seconds to wait for long polling. max 20")
def start(input_queue, output_queue, wait):
    click.echo("Processing starting")
    message_loop(input_queue, output_queue, wait)
    click.echo("Processing complete")


@main.command()
@click.option("--queue", default=INPUT_QUEUE, help="queue name to use as input queue")
def sample_data_loader(queue):
    click.echo("sample this!")
    sample_data(queue)
    click.echo("sample data (probably) loaded into input queue")
