import os

import boto3
from click.testing import CliRunner
from moto import mock_sqs

from submitter.cli import main

os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@mock_sqs
def test_cli_sample_data_loader():
    mocked_sqs = boto3.resource("sqs")
    input_queue = "test-input"
    queue = mocked_sqs.create_queue(QueueName=input_queue)

    # confirm queue starts empty
    sqs_messages = queue.receive_messages()
    assert len(sqs_messages) == 0

    runner = CliRunner()
    result = runner.invoke(main, ["sample-data-loader", "--queue", input_queue])
    assert result.exit_code == 0

    # confirm messages now in queue
    sqs_messages = queue.receive_messages()
    assert len(sqs_messages) > 0


@mock_sqs
def test_cli_start():
    mocked_sqs = boto3.resource("sqs")
    input_queue = "test-input"
    output_queue = "test-output"
    queue = mocked_sqs.create_queue(QueueName=input_queue)
    out = mocked_sqs.create_queue(QueueName=output_queue)

    # confirm queue starts empty
    sqs_messages = queue.receive_messages()
    assert len(sqs_messages) == 0

    runner = CliRunner()
    result = runner.invoke(main, ["sample-data-loader", "--queue", input_queue])
    assert result.exit_code == 0

    # confirm messages now in queue
    sqs_messages = queue.receive_messages()
    assert len(sqs_messages) > 0

    # confirm no messages in out queue before start
    out_messages = out.receive_messages()
    assert len(out_messages) == 0

    result = runner.invoke(
        main,
        [
            "start",
            "--wait",
            1,
            "--input-queue",
            input_queue,
            "--output-queue",
            output_queue,
        ],
    )
    assert result.exit_code == 0

    # confirm queue is empty again
    sqs_messages = queue.receive_messages()
    assert len(sqs_messages) == 0

    out_messages = out.receive_messages()
    assert len(out_messages) > 0
