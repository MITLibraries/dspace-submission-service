# 5. Process all documents in the queue every run

Date: 2021-09-02

## Status

Accepted

## Context

There is more than one solution to how to trigger this application to run, where it runs, and how much work the
application will do in a single run. These options affect not on the infrastructure, but also how the application is
designed.

They don't affect how applications using this service will interact, which remains directly writing to and reading from
SQS queues. This is solely about when and how to process the queues.

### Lambda

AWS Lambda can trigger for each message that lands in SQS. In this model, this application would process the single SQS
message that triggered the lamda.

Pros:

- Fully automated
- Solves "when to run" problem cleanly

Cons:

- Lambda can scale much faster than our DSpace instance and extreme care would be needed to ensure we don't DOS our
  DSpace in our normal submission work
- We don't have any experience in working with Lambda, SQS, or containers in this design pattern and our initial
  exploration showed it would require us to design the application to run in Lambda (even if we containerize) rather
  than just making an application that works and deploying as a container (for example in Fargate) which leads to more
  complex development environments

### Manual Trigger Fargate

Pros:

- we can develop the application to run locally and containerize that without taking any specific AWS Lambda
  requirements into account which will result in much more efficient development and ongoing maintenance
- the main message loop happens in the python app which means one message processed at a time so we can be sure to not
  flood DSpace (we could still scale out the number of Fargate tasks to run more concurrent submissions if needed in
  the future)

Cons:

- someone has to click "run". Long term this is not acceptable, but initially this is not as bad as it sounds as we only
  run 3 times a year for ETD and 12 times a year for Wiley.

### Clock Trigger Fargate

This could be a future addition to the Manual Trigger Fargate solution above.

Pros:

- Same as Manual Trigger Fargate
- Solves the "manual click" annoyance

Cons:

- Still doesn't run as soon as data is added to the queue. For instance, if data is submitted at 8am and our clock runs
  daily at 11pm we'd have several hours of unnecessary delay. Obviously we can run more frequently (such as hourly) to
  reduce the unnecessary delay, but never really eliminate it.

### Special 'go now' message

This service could define a specific SQS message that lambda could be listening for that signals all messages in a batch
have been sent and processing can start.

Pros:

- Same as Manual Trigger Fargate
- Processing can start immediately

Cons:

- adds complexity to the applications using this service as they'd need to not only send the data, but also the
  "please do work now"
- adds complexity to our infrastructure (having both a lambda and a fargate task)

### Airflow

Pros:

- Airflow can handle the SQS polling to know when to run
- Airflow can handle the error queues for applications that prefer not to handle it themselves (i.e that might not
  have a strong need to store state locally, such as Wiley)

Cons:

- Our current Airflow instance is out of date and a bit fragile, so we'd want to upgrade / move it to a vended service
  before considering this option

## Decision

We will build out the Manual Trigger Fargate option for initial release and process all documents in the queue on every
run.

We will then evaluate further which method, either documented above or something we have not yet considered, of
automation to implement. Leaving it as a manual process only is not intended.

## Consequences

Allowing development to proceed with no special knowledge of Lambda outweighs any other cons.

Looping over the entire queue on each run also allows for a simpler local development environment (i.e. we don’t need to
trigger the local application via lambda, we can just run it and it’ll loop over the queue it is connected to which can
either be a moto queue or a real AWS SQS queue depending on the needs at the time).

As we gain more knowledge of both the requirements and of options in AWS, we can evaluate which method of automation
best fits the problem and our team.
