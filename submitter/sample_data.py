import json

import boto3


def sample_data_loader(id, source, target, col_hdl, meta_loc, filename, fileloc, queue):
    sqs = boto3.resource("sqs")
    queue = sqs.get_queue_by_name(QueueName=queue)
    body = {
        "SubmissionSystem": target,
        "CollectionHandle": col_hdl,
        "MetadataLocation": meta_loc,
        "Files": [
            {"BitstreamName": filename, "FileLocation": fileloc},
        ],
    }
    # Send message to SQS queue
    queue.send_message(
        MessageAttributes={
            "PackageID": {"DataType": "String", "StringValue": id},
            "PackageSource": {"DataType": "String", "StringValue": source},
        },
        MessageBody=(json.dumps(body)),
    )


def sample_data(queue):
    sample_data_loader(
        "123",
        "ETD",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        queue,
    )
    sample_data_loader(
        "466",
        "ETD",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        queue,
    )
    sample_data_loader(
        "789",
        "ETD",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        queue,
    )
    sample_data_loader(
        "asd",
        "Wiley",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        queue,
    )
    sample_data_loader(
        "feg",
        "Wiley",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        queue,
    )
    sample_data_loader(
        "hij",
        "Wiley",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        queue,
    )
    sample_data_loader(
        "etd_123",
        "ETD",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        queue,
    )
    sample_data_loader(
        "wiley_456",
        "Wiley",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        queue,
    )
    sample_data_loader(
        "orange",
        "ETD",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        queue,
    )
    sample_data_loader(
        "cat",
        "popcorn",
        "devnull",
        "whatever",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        queue,
    )
