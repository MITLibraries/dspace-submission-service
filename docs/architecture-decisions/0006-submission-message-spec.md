# 6. Submission message spec

Date: 2021-09-09

## Status

amends [3. Submission message spec](0003-submission-message-spec.md)

Superceded by [8. Move message specifications](0008-move-specifications.md)

See [Submission Message Specification](../specifications/submission-message-specification.md)
for current version of this spec.

## Context

See [3. Submission message spec](0003-submission-message-spec.md) for additional context.

As we started to think about how this service will scale as more upstream applications start using it, we realized we
were putting coordination of queues responsibility into the service. For one or two apps, that is not unreasonable, but
for each new app the logistics could get unwieldy and alternate solutions are appropriate to consider.

## Decision

To simplify the logic in this DSpace Submission Service (DSS), the applications using DSS must provide the output queue
name they expect to be reading the success/errors back from.

### MessageAttributes

MessageAttributes is a JSON object containing one item, PackageID, structured
like so:

```json
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

see [3. Submission message spec](0003-submission-message-spec.md)

## Consequences

By having the submitting application be responsible for telling this service what output queue it expects to read
messages back from, it allows for the service to scale up more easily with less (or hopefully no) custom code per
submitting service.

Since the submitting application already needs to know what output queue to read from to get messages back, this does
not add any additional responsibility to the submitting app while reducing the responsibility of this service.

There is no change for the Infrastructure associated with this. All SQS queues are created and permissions assigned in
the same way they already are being managed. A submitting application cannot use an arbitrary Output queue, it needs to
have been created and permissions assigned prior to being used.
