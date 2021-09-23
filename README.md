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

## Sample Data

`pipenv run submitter sample-data-loader` will load some sample data into the SQS input queue

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
