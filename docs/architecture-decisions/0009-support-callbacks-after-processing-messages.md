# 9. Support callbacks after processing messages

Date: 2022-05-04

## Status

Accepted

## Context

DSS currently requires manual intervention. This was accepted during the initial build-out, but now that it has stabilized in production it is time to provide the ability for applications to move to full automation.

Triggering DSS to run after a batch has been submitted is already possible using direct AWS calls so DSS will not concern itself with how that works. For instance, ETD knows when it has finished populating the SQS queue and can easily add a call to start the fargate task directly that time if permissions are updated in AWS to allow that. Wiley should be able to do this as well. So starting processing on the incoming queue will be solved in the upstream applications.

To allow the upstream applications to know when to process their output queues, we'll need to make a change to both the incoming message specification and the application logic. This will be optional. Upstream applications can choose to continue to manually trigger DSS and the processing of output queues if they have reason to prefer that.

We'll update the incoming message spec to allow for including a callback URL in each message. Upstream applications can provide a URL that will alert them to process the output queue. As many uses cases will be to only receive one callback for a batch, DSS will keep track of all callback URLs during a processing batch and when it receives no additional SQS messages to process, it will add a step to call each _unique_ URL it encountered. The ETD application will listen on a route for this and then kick off it's existing output messaging logic. Wiley could consider creating a lambda that is triggered by a URL and providing that to DSS and then put any processing logic for the output queue in that lambda.

## Decision

We will allow an optional Callback URL in the input message to DSS.

Upon finishing processing incoming messages, DSS will call all unique callback URLs it encountered.

Upstream applications will be responsible for starting DSS incoming queue processing.

## Consequences

This will allow optional full automation of the DSS publishing pipeline while not introducing constant polling or introducing delays by only running queues at specific times of the day or week.

Messages will be processed immediately and upstream applications will be alerted as soon as their content has been published or has errored.
