# DSpace Submission Service

A service for creating DSpace records and attaching metadata
and bitstreams.

This application will read from input queues, create DSpace records, and write
results to output queues.

## Development

Clone the repo and install the dependencies using [Pipenv](https://docs.pipenv.org/):

```bash
git clone git@github.com:MITLibraries/dspace-submission-service.git
cd dspace-submission-service
pipenv install --dev
pipenv run submitter --help
```

The [Click documentation](https://click.palletsprojects.com/en/8.0.x/quickstart/)
will be helpful to understand how to create and run commands.

## Using Moto for local SQS queues

It is often desireable to use [Moto](https://github.com/spulec/moto) for local development using the [Standalone Server Mode(https://github.com/spulec/moto#stand-alone-server-mode)] rather than using true AWS SQS queues.

To use, start moto running sqs in standalone mode with `pipenv run moto_server`, then:

- add `SQS_ENDPOINT_URL='http://localhost:5000'` to your `.env` file
- create the queues you'd like to use
  - pipenv run submitter create-queue YOUR_INPUT_QUEUE
  - pipenv run submitter create-queue YOUR_OUTPUT_QUEUE

While this provides local SQS queues, please note it does not provide local DSpace so you currently still need to use the test server and real credentials.

## Local development with DSpace

[Please insert instructions here!!]

If you are just interested in testing SQS aspects of the application, you can bypass
DSpace Submission (in Development only) by adding `SKIP_PROCESSING=true` to your `.env` file

## Sample Data

`pipenv run submitter sample-data-loader --input-queue=YOUR_INPUT_QUEUE --output-queue=YOUR_OUTPUT_QUEUE` will load some sample data into the SQS input queue

Warning: please do not run this against the production system or a bunch of junk records
will load into dspace

## Processing

`pipenv run submitter start` will loop through all of the data in the SQS input queue, process the queue,
write to the output queue, delete the messages from the input queue, and then shutdown when no
more messages are returned from the input queue

## Docker

```bash
make dist
docker run submitter:latest --
```

note: the application requires being run in an environment with Roles based access to the AWS resources. in addition, the environment must have WORKSPACE and SSM_PATH variables set according to stage and prod conventions.
