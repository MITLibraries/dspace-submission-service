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
make install
pipenv run submitter --help
```

The [Click documentation](https://click.palletsprojects.com/en/8.0.x/quickstart/)
will be helpful to understand how to create and run commands.

Set env variables in `.env` file as needed:
- WORKSPACE: required, "dev" is a good value for local development
- DSPACE_API_URL: only needed if publishing to DSpace, use DSpace test instance for
  development
- DSPACE_USER: only needed if publishing to DSpace
- DSPACE_PASSWORD: only needed if publishing to DSpace
- DSPACE_TIMEOUT: only needed if publishing to DSpace, defaults to 120 seconds
- INPUT_QUEUE: input message queue to use for development (see section below on
  using Moto for local SQS queues)
- LOG_FILTER: filters out logs from external libraries, defaults to "true".
  Can be useful to set this to "false" if there are errors that seem to involve
  external libraries whose debug logs may have more information
- LOG_LEVEL: level for logging, defaults to INFO. Can be useful to set to DEBUG for
  more detailed logging
- OUTPUT_QUEUES: comma-separated string list of valid output queues, defaults to
  "output". Update if using a different name for the output queue(s) in development
- SKIP_PROCESSING: skips the publishing process for messages, defaults to "true". Can
  be useful for working on just the SQS components of the application. Set to "false"
  if messages should be processed and published
- SQS_ENDPOINT_URL: needed if using Moto for local development (see section below)


### Using Moto for local SQS queues

It is often desireable to use [Moto](https://github.com/spulec/moto) for local development using the [Standalone Server Mode(https://github.com/spulec/moto#stand-alone-server-mode)] rather than using true AWS SQS queues.

To use, start moto running sqs in standalone mode with `pipenv run moto_server`, then:

- add `SQS_ENDPOINT_URL='http://localhost:5000'` to your `.env` file
- create the queues you'd like to use
  - pipenv run submitter create-queue YOUR_INPUT_QUEUE
  - pipenv run submitter create-queue YOUR_OUTPUT_QUEUE

While this provides local SQS queues, please note it does not provide local DSpace so you currently still need to use the test server and real credentials.

### Local development with DSpace

If you are just interested in testing SQS aspects of the application, you can bypass
DSpace Submission (in Development only) by adding `SKIP_PROCESSING=true` to your `.env`
file.

For local development, the default request timeout for requests sent to the DSpace API
is 120 seconds due to slow response times from our test DSpace instance. However, this
can make troubleshooting the DSpace connection tricky. To set a shorter (or longer if
needed) timeout, add `DSPACE_TIMEOUT=<seconds as a float, e.g. 2.0>` to your `.env`
file.

## Sample Data

`pipenv run submitter load-sample-data -i=YOUR_INPUT_QUEUE -o=YOUR_OUTPUT_QUEUE` will
load some sample data into the SQS input queue. If you want to load data for
integration testing with DSpace test, add an additional option to the command:
`-f tests/fixtures/integration-test-submission-messages.json`.

Warning: please do not run this against the production system or a bunch of junk records
will load into dspace

## Processing

`pipenv run submitter start` will loop through all of the data in the SQS input queue, process the queue,
write to the output queue, delete the messages from the input queue, and then shutdown when no
more messages are returned from the input queue

## Docker

Note: The application requires being run with `WORKSPACE` env variable set to an environment (`dev`, `stage`, or `prod`). Use credentials from the `dss-management-sso-policy` for the desired environment in order to access the necessary AWS resources.

```bash
make dist-<environment>
docker run submitter:latest --
```

## Makefile Info
The `Makefile` contains commands for running the application in the `dev`, `stage`, and `prod` environments as an ECS task. 

The commands are produced by the Terraform used to create the infrastructure and copy/pasted here for convenience. Calling each command will execute the latest version of the container in the specified environment.