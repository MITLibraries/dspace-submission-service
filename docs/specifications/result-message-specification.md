# Result Message Specification

## Context

Multiple external applications will read from the SQS result queues used by this
service, so we need a specification to ensure consistent messages containing
all data required for the consuming applications to process them.

All messages that have been processed from the input queue will have
corresponding result messages in the output queue regardless of success or
failure of submission to DSpace.

Note that all consuming applications will need to delete each message from the result queue when they have successfully processed it.

## Specification

Each SQS Message sent by the dspace-submission-service to one of its result
queues will contain two components, MessageAttributes and MessageBody.

### MessageAttributes

MessageAttributes must be a JSON object containing two items, PackageID and
SubmissionSource, structured as follows:

```
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

MessageBody must be a string representation of a JSON object, containing detailed
information about the submission result. The specification is slightly different for success results and error results, structured as follows.

Note: SQS requires that the MessageBody be a string. However, this service and
the submitting applications will want to parse/create the MessageBody as JSON
objects, so the specification here shows the JSON object structure. This
service must convert the MessageBody to a string before sending
the message and the consuming applications must parse it back into a JSON
object when processing messages from the result queue.

#### Success Result

```
MessageBody = {
    "ResultType": "success",
    "ItemHandle": "Handle of the successfully created new item in DSpace, e.g.
        '1721.1/98765'",
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
            The above object may be repeated as needed for all bitstreams associated with the item.
        }
    ]
}
```

#### Error Result

```
MessageBody = {
    "ResultType": "error",
    "ErrorTimestamp": "Timestamp when the error occurred. Provided to help external
        service maintainers investigate the issue",
    "ErrorInfo": "Information provided by the DSpace Submission Service about
        where in the process the error occurred, e.g. 'Error occurred while
        posting item to DSpace'",
    "DSpaceResponse": "Response message provided by DSpace if the error was caused by a
        DSpace exception. If the error was not caused by a DSpace exception, this value
        will be 'N/A'",
    "ExceptionTraceback": "Full stack trace of the Exception"
}
```

## Examples

### Success Result Message Example

```json
MessageAttributes = {
    "PackageID": {
        "DataType": "String",
        "StringValue": "12345"
    },
    "SubmissionSource": {
        "DataType": "String",
        "StringValue": "ETD"

    }
}

MessageBody = {
    "ResultType": "success",
    "ItemHandle": "1721.1/98765",
    "lastModified": "Thu Dec 09 18:24:57 UTC 2021",
    "Bitstreams": [
        {
            "BitstreamName": "very-important-thesis.pdf",
            "BitstreamUUID": "443e63c4-467f-4e74-a3b9-5bcd297bba0c",
            "BitstreamChecksum": {
                    "value": "a4e0f4930dfaff904fa3c6c85b0b8ecc",
                    "checkSumAlgorithm": "MD5"
            }
        },
        {
            "BitstreamName": "supplementary-file-01.tx",
            "BitstreamUUID": "de542c50-f97c-4f1a-84be-febe934f754f",
            "BitstreamChecksum": {
                    "value": "a4e0f4930dfaff904fa3c6c85b0b8ecc",
                    "checkSumAlgorithm": "MD5"
            }
        },
    ]
}
```

### Error Result Message Example

```json
MessageAttributes = {
    "PackageID": {
        "DataType": "String",
        "StringValue": "12345"
    },
    "SubmissionSource": {
        "DataType": "String",
        "StringValue": "ETD"

    }
}

MessageBody = {
    "ResultType": "error",
    "ErrorTimestamp": "2021-12-09 14:12:01",
    "ErrorInfo": "Error occurred while posting item to DSpace collection
        '1721.1/123456'",
    "DSpaceResponse": "<!doctype html><html lang=\"en\"><head>
        <title>HTTP Status 500 \u2013 Internal Server Error</title>
        <style type=\"text/css\">body {font-family:Tahoma,Arial,sans-serif;}
        h1, h2, h3, b {color:white;background-color:#525D76;} h1 {font-size:22px;}
        h2 {font-size:16px;} h3 {font-size:14px;} p {font-size:12px;} a {color:black;}
        .line {height:1px;background-color:#525D76;border:none;}</style></head>
        <body><h1>HTTP Status 500 \u2013 Internal Server Error</h1>
        <hr class=\"line\" /><p><b>Type</b> Status Report</p><p><b>Message</b>
        Internal Server Error</p><p><b>Description</b> The server encountered an unexpected condition that prevented it from fulfilling the request.</p>
        <hr class=\"line\" /><h3>Apache Tomcat/7.0.109</h3></body></html>",
    "ExceptionTraceback": [
        "Traceback (most recent call last):",
        "File \"/dspace-submission-service/submitter/submission.py\", line 205, in
            post_item",
        "item.post(client, collection_handle=collection_handle)",
        "File \"/dspace-submission-service-9hfb6nVJ-python/lib/python3.9/site-packages/
            dspace/item.py\", line 124, in post",
        "collection_id = select_identifier(client, collection_handle, collection_uuid)",
        "File \"/dspace-submission-service-9hfb6nVJ-python/lib/python3.9/site-packages/
            dspace/utils.py\", line 37, in select_identifier",
        "retrieved_uuid = client.get_object_by_handle(handle).json()[\"uuid\"]",
        "File \"/dspace-submission-service-9hfb6nVJ-python/lib/python3.9/site-packages/
            dspace/client.py\", line 132, in get_object_by_handle",
        "response = self.get(endpoint)",
        "File \"/dspace-submission-service-9hfb6nVJ-python/lib/python3.9/site-packages/
            dspace/client.py\", line 111, in get",
        "response.raise_for_status()",
        "File \"/dspace-submission-service-9hfb6nVJ-python/lib/python3.9/site-packages/
            requests/models.py\", line 953, in raise_for_status",
        "raise HTTPError(http_error_msg, response=self)",
        "requests.exceptions.HTTPError: 500 Server Error: Internal Server Error for
            url: https://dspace.mit.edu/rest/handle/1721.1/123456",
        "The above exception was the direct cause of the following exception:",
        "Traceback (most recent call last):",
        "File \"/Users/hbailey/Dropbox (MIT)/Dev/mit-localdev/dspace-submission-service/
            submitter/submission.py\", line 174, in submit",
        "post_item(client, item, self.collection_handle)",
        "File \"/dspace-submission-service/submitter/submission.py\", line 210, in
            post_item",
        "raise errors.ItemPostError(e, collection_handle) from e",
        "submitter.errors.ItemPostError: (HTTPError('500 Server Error: Internal Server
            Error for url: https://dspace.mit.edu/rest/handle/1721.1/123456'),
            '1721.1/not-a-collection')"
    ]
}
```
