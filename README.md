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
submitter --help
```

The [Click documentation](https://click.palletsprojects.com/en/8.0.x/quickstart/)
will be helpful to understand how to create and run commands.

## Docker

```bash
make dist
docker run submitter:latest --
```
