from click.testing import CliRunner

from submitter.cli import main


def test_cli_sample_data_loader(mocked_sqs):
    queue = mocked_sqs.get_queue_by_name(QueueName="empty_input_queue")

    sqs_messages = queue.receive_messages()
    assert len(sqs_messages) == 0

    runner = CliRunner()
    result = runner.invoke(main, ["sample-data-loader", "--input_queue",
                           "empty_input_queue", "--output_queue", "empty_result_queue"])
    assert result.exit_code == 0

    sqs_messages = queue.receive_messages()
    assert len(sqs_messages) > 0


def test_cli_start(caplog, mocked_dspace, mocked_sqs):
    # Required because pytest and CliRunner handle log capturing in incompatible ways
    caplog.set_level(100000)
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
