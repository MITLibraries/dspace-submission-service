# DSpace Submission Service

A service for creating DSpace records and attaching metadata
and bitstreams.

This application will read from input queues, create DSpace records, and write
results to output queues.

## Development

Clone the repo and install the dependencies using `make install`:

```bash
git clone git@github.com:MITLibraries/dspace-submission-service.git
cd dspace-submission-service
make install
uv run submitter --help
```

The [Click documentation](https://click.palletsprojects.com/en/8.0.x/quickstart/)
will be helpful to understand how to create and run commands.

### Using Moto for local SQS queues

It is often desireable to use [Moto](https://github.com/spulec/moto) for local development using the [Standalone Server Mode(https://github.com/spulec/moto#stand-alone-server-mode)] rather than using true AWS SQS queues.

To use, start moto running sqs in standalone mode with `uv run moto_server`, then:

- add `SQS_ENDPOINT_URL='http://localhost:5000'` to your `.env` file
- create the queues you'd like to use
  - uv run submitter create-queue YOUR_INPUT_QUEUE
  - uv run submitter create-queue YOUR_OUTPUT_QUEUE

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

`uv run submitter load-sample-data -i=YOUR_INPUT_QUEUE -o=YOUR_OUTPUT_QUEUE` will
load some sample data into the SQS input queue. If you want to load data for
integration testing with DSpace test, add an additional option to the command:
`-f tests/fixtures/integration-test-submission-messages.json`.

Warning: please do not run this against the production system or a bunch of junk records
will load into dspace

## Verifying DSpace connection
To verify that DSS can connect to the DSpace REST API, run `make verify-dspace-connection` and view the logs to see if the connection was successful or failed.

## Processing

`uv run submitter start` will loop through all of the data in the SQS input queue, process the queue,
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


## Environment Variables

### Required

```shell
WORKSPACE=#Set to `dev` for local development, this will be set to `stage` and `prod` in those environments by Terraform.
DSS_DSPACE_CREDENTIALS=#A collection of DSpace credentials formatted as a JSON string, where the key is a short name for a DSpace repository indicated in submission messages and values are credentials for a user account with keys for url, user, and password.
INPUT_QUEUE=#Input message queue to use for development (see section below on using Moto for local SQS queues)
OUTPUT_QUEUES=#Comma-separated string representing a list of valid output queues.
```

### Optional

```shell
SENTRY_DSN=#If set to a valid Sentry DSN, enables Sentry exception monitoring. This is not needed for local development.
DSPACE_TIMEOUT=#Request time out for DSpace, defaults to 180 seconds.
LOG_FILTER=# filters out logs from external libraries, defaults to "true". Can be useful to set this to "false" if there are errors that seem to involve external libraries whose debug logs may have more information
LOG_LEVEL=# level for logging, defaults to INFO. Can be useful to set to DEBUG for more detailed logging
SKIP_PROCESSING=#Skip ingesting items into DSpace, defaults to "false".
SQS_ENDPOINT_URL=#URL of the entry point for SQS. Only needed if using Moto for local development. Defaults to None; in `prod`, botocore will automatically construct the appropriate URL to use when communicating with a service.
WARNING_ONLY_LOGGERS=#Comma-separated list of logger names to set as WARNING only, e.g. 'botocore,smart_open,urllib3'.
```


## Related Assets

This is a repository that provides the DSpace Submission Service. The following application infrastructure repositories are related to this repository:

* [DSO Infrastructure](https://github.com/MITLibraries/mitlib-tf-workloads-dso)
* [ECR](https://github.com/MITLibraries/mitlib-tf-workloads-ecr)

## Maintainers

* Owner: See [CODEOWNERS](./.github/CODEOWNERS)
* Team: See [CODEOWNERS](./.github/CODEOWNERS)
* Last Maintenance: 2026-02
