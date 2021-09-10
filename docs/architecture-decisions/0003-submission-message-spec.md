# 3. Submission message spec

Date: 2021-08-25

## Status

Accepted

Amended by [6. Submission message spec](0006-submission-message-spec.md)

## Context

Multiple external applications will write to the SQS submit queue used by this
service, so we need a specification they can follow to create consistent
messages containing all data required for submitting an item to DSpace.

## Decision

We will use the following submission message specification:

Each SQS Message sent to the dspace-submission-service submit queue will
contain two components, MessageAttributes and MessageBody.

### MessageAttributes

[Important: See Updated MessageAttributes in 6. Submission message spec](0006-submission-message-spec.md)

MessageAttributes is a JSON object containing one item, PackageID, structured
like so:

```
MessageAttributes = {
    "PackageID": {
        "DataType": "String",
        "StringValue": "<A unique ID created by the submitting application that
            will allow said application to match the result information to each
            submitted package, e.g. 'etd_123123' or '98765'. This system is agnostic about the value of the ID.>"
    },
    "SubmissionSource": {
        "DataType": "String",
        "StringValue": "<Name of the submitting system, e.g. 'ETD'. Should be
            consistent for each submitting system (should not change over
            time).>"

    }
}
```

### MessageBody

SQS requires that the MessageBody be a string. However, this service and the
submitting applications will want to parse/create the MessageBody as JSON
objects, so the specification here shows the JSON object structure. The
submitting application must convert the MessageBody to a string before sending
the message and this service will parse it back into a JSON object when
processing messages from the submit queue.

```
MessageBody = {
    "SubmissionSystem": "Required - specific system to submit to, e.g.
        'DSpace@MIT'"
    "CollectionHandle": "Required - handle for DSpace Collection to post item
        to, e.g. '1721.1/131022'",
    "MetadataLocation": "Required - S3 URI for item metadata JSON file, e.g.
        'S3://bucket/metadata_file.json>'",
    "Files": [
        {
            "BitstreamName": "Required - name of Bitstream in DSpace, e.g.
                'baker_report.pdf'",
            "FileLocation": "Required - S3 URI for Bitstream file , e.g.
                'S3://bucket/baker_report.pdf'",
            "BitstreamDescription": "Optional - description of Bitstream
                in DSpace, e.g. 'The Baker Report'"
        },
        {
            "(At least one file object required. Repeat for all files in item.)"
        }
    ]
}
```

## Consequences

All applications submitting messages to this service will need to follow this specification.

All messages submitted following this specification should be successfully parsed and processed by the DSpace Submission Service. Note that this does not guarantee the submission will be successfully added to DSpace.

Messages that do not follow this specification will be rejected and sent to the result queue with a useful error message for the submitting application to handle.
