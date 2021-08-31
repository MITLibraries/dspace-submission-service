import click

from submitter.sample_data import sample_data
from submitter.sqs import message_loop


@click.group()
def main():
    pass


@main.command()
def start():
    click.echo("Processing starting")
    message_loop()


@main.command()
def sample_data_loader():
    click.echo("sample this!")
    sample_data()
    click.echo("sample data (probably) loaded into input queue")
