import pytest
from botocore.exceptions import ClientError

from submitter.sqs import (
    create,
    message_loop,
    process,
    retrieve_messages_from_queue,
    sqs_client,
    write_message_to_queue,
)


def test_sqs_client_returns_sqs_resource():
    sqs = sqs_client()
    type_as_string = type(sqs).__name__

    assert "sqs.ServiceResource" == type_as_string


def test_create(mocked_sqs):
    # confirm queue does not exist
    test_queue = "testing_123"
    c = sqs_client()
    with pytest.raises(ClientError) as e:
        c.get_queue_by_name(QueueName=test_queue)
        assert (
            e.value.response["Error"]["Code"]
            == "AWS.SimpleQueueService.NonExistentQueue"
        )

    # create queue
    create(test_queue)

    # confirm queue exists
    q = c.get_queue_by_name(QueueName=test_queue)
    assert "sqs.Queue" == type(q).__name__


def test_retrieve_messages_from_queue(mocked_sqs):
    msgs = retrieve_messages_from_queue("input_queue_with_messages", 0)
    assert len(msgs) == 10


def test_write_message_to_queue(mocked_sqs, raw_attributes, raw_body):
    # confirm queue starts empty
    msgs = retrieve_messages_from_queue("empty_result_queue", 0)
    assert len(msgs) == 0

    # write to queue
    write_message_to_queue(raw_attributes, raw_body, "empty_result_queue")

    # confirm queue has a message
    msgs = retrieve_messages_from_queue("empty_result_queue", 0)
    assert len(msgs) == 1


def test_process(mocked_sqs, mocked_dspace):
    msgs = retrieve_messages_from_queue("input_queue_with_messages", 0)

    # confirm initial length of messages
    assert len(msgs) == 10

    output_msgs = retrieve_messages_from_queue("empty_result_queue", 0)
    assert len(output_msgs) == 0

    # process
    process(msgs)

    # confirm input queue is empty
    msgs = retrieve_messages_from_queue("input_queue_with_messages", 0)
    assert len(msgs) < 10

    # confirm output queue is populated
    output_msgs = retrieve_messages_from_queue("empty_result_queue", 0)
    assert len(output_msgs) > 0


def test_message_loop(mocked_sqs, mocked_dspace):
    # confirm initial length of messages
    # passing visibility as zero so the message_loop can access the messages
    msgs = retrieve_messages_from_queue("input_queue_with_messages", 0, 0)
    assert len(msgs) == 10

    output_msgs = retrieve_messages_from_queue("empty_result_queue", 0)
    assert len(output_msgs) == 0

    # process
    message_loop("input_queue_with_messages", 0, 0)

    # confirm input queue is empty
    msgs = retrieve_messages_from_queue("input_queue_with_messages", 0, 0)
    assert len(msgs) == 0

    # confirm output queue is populated
    output_msgs = retrieve_messages_from_queue("empty_result_queue", 0)
    assert len(output_msgs) == 10
