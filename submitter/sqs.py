import boto3
import click


def message_loop():
    msgs = retrieve()

    if len(msgs) > 0:
        click.echo(len(msgs))
        process(msgs)
        message_loop()
    else:
        click.echo("No messages received")


def process(msgs):
    for message in msgs:
        click.echo(message.message_attributes)
        click.echo(message.body)
        print("Do all the dspace submission stuff here")

        # faking it with always succeeding for now... creating of this status
        # dict is likely better moved to our upcoming submission class but this
        # was convenient for initial testing
        status = {
            "PackageSource": {
                "DataType": "String",
                "StringValue": message.message_attributes.get("PackageSource").get(
                    "StringValue"
                ),
            },
            "PackageID": {
                "DataType": "String",
                "StringValue": message.message_attributes.get("PackageID").get(
                    "StringValue"
                ),
            },
            "status": {"DataType": "String", "StringValue": "success"},
            "handle": {
                "DataType": "String",
                "StringValue": "https://example.com/handle/this",
            },
        }

        # write result to output
        write(status)

        # cleanup (probs better to confirm the write to the output was good
        # before cleanup but for now yolo it)
        message.delete()


def retrieve():
    sqs = boto3.resource("sqs")
    queue = sqs.get_queue_by_name(QueueName="queue1-stage")

    click.echo("Polling for messages")
    msgs = queue.receive_messages(
        MaxNumberOfMessages=10,
        WaitTimeSeconds=20,
        MessageAttributeNames=["All"],
        AttributeNames=["All"],
    )

    return msgs


def write(status):
    sqs = boto3.resource("sqs")
    queue = sqs.get_queue_by_name(QueueName="queue2-stage")

    # Send message to SQS result queue
    queue.send_message(
        MessageAttributes=status,
        MessageBody=("testing"),
    )
