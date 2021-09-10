# 7. Result message spec

Date: 2021-09-10

## Status

Accepted

## Context

Multiple external applications will read from the SQS result queues used by this
service, so we need a specification to ensure consistent messages containing
all data required for the consuming applications to process them.

## Decision

We will use the following result message specification:

Each SQS Message sent by the dspace-submission-service to one of its result
queues will contain two components, MessageAttributes and MessageBody.

### MessageAttributes

MessageAttributes is a JSON object containing two items, PackageID and
SubmissionSource, structured like so:

```json
MessageAttributes = {
    "PackageID": {
        "DataType": "String",
        "StringValue": "<A unique ID created by the submitting application that
            will allow said application to match the result information to each
            submitted package, e.g. 'etd_123123' or '98765'. The PackageID of
            the result message must match the PackageID from the corresponding
            submit message.>"
    },
    "SubmissionSource": {
        "DataType": "String",
        "StringValue": "<Name of the submitting system, e.g. 'ETD'. The
          SubmissionSource of the result message must match the
          SubmissionSource from the corresponding submit message.>"
    }
}
```

### MessageBody

The MessageBody will contain detailed information about the submission result.
The specification is slightly different for success results and error results.

Note: SQS requires that the MessageBody be a string. However, this service and
the submitting applications will want to parse/create the MessageBody as JSON
objects, so the specification here shows the JSON object structure. This
service must convert the MessageBody to a string before sending
the message and the consuming applications must parse it back into a JSON
object when processing messages from the result queue.

#### Success Result

```json
MessageBody = {
    "ResultType": "success",
    "ItemHandle": "Handle of the successfully created new item in DSpace, e.g.
        '1721.1/131022'",
    "lastModified": "Timestamp the item was last modified in DSpace, e.g. 'Thu
        Sep 09 17:56:39 UTC 2021'",
    "Bitstreams": [
        {
            "BitstreamName": "Name of the Bitstream in DSpace, e.g.
                'baker_report.pdf'",
            "BitstreamUUID": "UUID of the Bitstream in DSpace",
            "BitstreamChecksum": "JSON object with the value and hash algorithm
                of the DSpace-calculated checksum as supplied by the bitstream
                post, e.g.
                {
                    'value': 'a4e0f4930dfaff904fa3c6c85b0b8ecc',
                    'checkSumAlgorithm': 'MD5'
                }"
        },
        {
            "(Repeat for all bitstreams posted with item.)"
        }
    ]
}
```

#### Error Result

```json
MessageBody = {
    "ResultType": "error",
    "ErrorInfo": "Information provided by the DSpace Submission Service about
        where in the process the error occurred, e.g. 'Error occurred while
        posting item to DSpace'",
    "ExceptionMessage": "String representation of the Exception message, e.g.
        '500 Server Error: Internal Server Error'",
    "ExceptionTraceback": "Full unformatted stack trace of the Exception"
}
```

## Consequences

Consuming applications will be able to handle result messages appropriately as  
all messages posted to the result queue will follow this specification.

All messages that have been processed from the input queue will have
corresponding result messages in the output queue regardless of success or
failure of submission to DSpace.
