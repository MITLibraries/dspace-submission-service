import logging

from click.testing import CliRunner

from submitter.cli import main


def test_cli_load_sample_input_data(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")

    sqs_messages = queue.receive_messages()
    assert len(sqs_messages) == 0

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "load-sample-input-data",
            "--input-queue",
            "empty_input_queue",
            "--output-queue",
            "empty_result_queue",
        ],
    )
    assert result.exit_code == 0

    sqs_messages = queue.receive_messages()
    assert len(sqs_messages) > 0


def test_cli_load_sample_output_data(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_result_queue")

    sqs_messages = queue.receive_messages()
    assert len(sqs_messages) == 0

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "load-sample-output-data",
            "--output-queue",
            "empty_result_queue",
        ],
    )
    assert result.exit_code == 0

    sqs_messages = queue.receive_messages()
    assert len(sqs_messages) > 0


def test_cli_start(mocked_dspace6, mocked_sqs):
    input_queue = mocked_sqs.get_queue_by_name(QueueName="input_queue_with_messages")
    result_queue = mocked_sqs.get_queue_by_name(QueueName="empty_result_queue")

    results = result_queue.receive_messages()
    assert len(results) == 0

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "start",
            "--wait",
            1,
            "--queue",
            "input_queue_with_messages",
        ],
    )
    assert result.exit_code == 0

    sqs_messages = input_queue.receive_messages()
    assert len(sqs_messages) == 0
    out_messages = result_queue.receive_messages()
    assert len(out_messages) > 0


def test_verify_dspace_connection_success(mocked_dspace6, caplog):
    with caplog.at_level(logging.INFO):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "verify-dspace-connection",
            ],
        )
        assert result.exit_code == 0
        assert (
            "Successfully authenticated to mock://dspace.edu/rest/ as test" in caplog.text
        )


def test_verify_dspace_connection_failed(mocked_dspace6_auth_failure, caplog):
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "verify-dspace-connection",
        ],
    )
    assert result.exit_code == 0
    assert "Failed to authenticate to mock://dspace.edu/rest/ as test" in caplog.text
