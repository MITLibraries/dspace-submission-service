# DSpace Submission Service

A service for creating DSpace records and attaching metadata
and bitstreams. 

DSpace Submission Service (DSS) is a Python CLI application for ingesting items into DSpace.

This app consumes submission messages from designated input queues, which must be formatted according to the [Submission Message Specification](https://github.com/MITLibraries/dspace-submission-service/pull/docs/specifications/submission-message-specification.md). The content of the submission message tells the app where to find bitstreams and metadata for an [item](https://github.com/DSpace/RestContract/blob/main/items.md). This data is used to prepare an item that can be submitted to DSpace via the REST API. After sending a request to DSpace, DSS will write a result message to an output queue assigned to the submission source (see also [Result Message Specification](https://github.com/MITLibraries/dspace-submission-service/pull/docs/specifications/result-message-specification.md)).


## Development

* To preview a list of available Makefile commands: `make help`
* To install with dev dependencies: `make install`
* To update dependencies: `make update`
* To run unit tests: `make test`
* To lint the repo: `make lint`
* To run the app:
 * `uv run submitter start --queue <input-queue>`
    * requires activated project uv python environment
    * utilizes uv built entrypoint (see project.scripts in pyproject.toml)
    * does not support loading a .env file
  * `uv run --env-file .env submitter start --queue <input-queue>`
    * More verbose but supports loading a .env file


### Using Moto for local SQS queues

It is often desireable to use [Moto](https://github.com/spulec/moto) for local development using the [Standalone Server Mode](https://github.com/spulec/moto#stand-alone-server-mode) rather than using true AWS SQS queues.

To use, start moto running sqs in standalone mode with `uv run moto_server`, then:

- add `SQS_ENDPOINT_URL='http://localhost:5000'` to your `.env` file
- create the queues you'd like to use:
  - `uv run submitter create-queue <input-queue>`
  - `uv run submitter create-queue <output-queue>`

While this provides local SQS queues, please note it does not provide local DSpace so you currently still need to use the test server and real credentials.

### Local development with DSpace

If you are just interested in testing SQS aspects of the application, you can bypass
DSpace Submission (in Development only) by adding `SKIP_PROCESSING=true` to your `.env`
file.

The application supports submission to both DSpace 6 and DSpace 8 instances. For local development, the default request timeout for requests sent to the DSpace API
is 180 seconds. To set adjust the timeout, set `DSPACE_TIMEOUT=<seconds as a float, e.g. 30.0>` in your `.env` file.

## Sample Data

Load sample input data:
```bash
uv run submitter load-sample-input-data -i=YOUR_INPUT_QUEUE -o=YOUR_OUTPUT_QUEUE -f <sample data filepath>
```

For integration testing with DSpace test server, use:
```bash
uv run submitter load-sample-input-data -i=YOUR_INPUT_QUEUE -o=YOUR_OUTPUT_QUEUE -f tests/fixtures/integration-test-submission-messages.json
```

You can also load sample output data:
```bash
uv run submitter load-sample-output-data -o=YOUR_OUTPUT_QUEUE -f <sample data filepath>
```

Warning: please do not run this against the production system or a bunch of junk records
will load into DSpace

## Verifying DSpace connection

To verify that DSS can connect to a DSpace instance, run:

```bash
uv run submitter verify-dspace-connection --submission-system=<SUBMISSION_SYSTEM>
```

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
DSS_DSPACE_CREDENTIALS=#A JSON string containing credentials for all supported DSpace instances. Each entry requires 'url', 'user', and 'password' fields. Example: {"ir-6":{"url":"...","user":"...","password":"..."},"ddc-6":{...},"ir-8":{...},"ddc-8":{...}}
INPUT_QUEUE=#Input message queue to use for development (see section below on using Moto for local SQS queues).
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
