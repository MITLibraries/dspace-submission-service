# Submission Message Specification

## Context

Multiple external applications will write to the SQS submit queue used by this
service, so we need a specification they can follow to create consistent
messages containing all data required for submitting an item to DSpace.

All applications submitting messages to this service will need to follow this specification.

All messages submitted following this specification should be successfully parsed and processed by the DSpace Submission Service. Note that this does not guarantee the submission will be successfully added to DSpace.

Messages that do not follow this specification will be rejected and sent to the result queue with a useful error message for the submitting application to handle.

By having the submitting application be responsible for telling this service what
output queue it expects to read messages back from, it allows for the service to scale
up more easily with less (or hopefully no) custom code per submitting service.

## Specification

Each SQS Message sent to the dspace-submission-service submit queue must
contain two components, MessageAttributes and MessageBody.

### MessageAttributes

MessageAttributes must be a JSON object containing three items: PackageID,
SubmissionSource, and OutputQueue, structured as follows:

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

    },
    "OutputQueue": {
      "DataType": "String",
      "StringValue": "<Name of the pre-agreed upon output SQS queue to be used for the submitting system. The queue must
          already exist and both systems must have appropriate access to the queue.>"
    }
}
```

### MessageBody

MessageBody must be a string representation of a JSON object structured as follows.

NOTE: SQS requires that the MessageBody be a string. However, this service and the
submitting applications will want to parse/create the MessageBody as JSON
objects, so the specification here shows the JSON object structure. The
submitting application must convert the MessageBody to a string before sending
the message and this service will parse it back into a JSON object when
processing messages from the submit queue.

```
MessageBody = {
    "SubmissionSystem": "Required - specific system to submit to, e.g.
        'DSpace@MIT'",
    "CollectionHandle": "Required - handle for DSpace Collection to post item
        to, e.g. '1721.1/123456'",
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
            Repeat above object as needed for all files in item. At least one file
            object is required.

            NOTE: DSS will post the bitstreams to the item in the order they are
            present in this 'files' array of the message body. It is up to each
            submitting application to determine which file should be the primary
            bitstream for the item and ensure that file is the first one in this array
            (if there are multiple files). All other files present in this array should
            be listed in the order they should be displayed in DSpace, if there is a
            preference.
        }
    ]
}
```

## Example Submission Message

```json
MessageAttributes = {
    "PackageID": {
        "DataType": "String",
        "StringValue": "12345"
    },
    "SubmissionSource": {
        "DataType": "String",
        "StringValue": "ETD"

    },
    "OutputQueue": {
      "DataType": "String",
      "StringValue": "etd-dss-input-queue"
    }
}

MessageBody = {
    "SubmissionSystem": "DSpace@MIT",
    "CollectionHandle": "1721.1/123456",
    "MetadataLocation": "S3://bucket-7/item-12345-metadata-file.json>'",
    "Files": [
        {
            "BitstreamName": "very-important-thesis.pdf",
            "FileLocation": "S3://bucket-7/thesis-12345.pdf'",
            "BitstreamDescription": "Thesis PDF"
        },
        {
            "BitstreamName": "supplementary-file-01.txt",
            "FileLocation": "S3://bucket-7/thesis-12345-supplement-1.txt",
            "BitstreamDescription": "Supplementary file"
        }
    ]
}
```
