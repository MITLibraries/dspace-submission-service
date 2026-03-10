# ruff: noqa: SIM300
import json
import os

import pytest

from submitter.config import Config


def test_config_without_workspace_env_raises_error():
    del os.environ["WORKSPACE"]
    with pytest.raises(KeyError):
        Config()


def test_config_from_env_success():
    os.environ["WORKSPACE"] = "stage"
    config = Config()
    assert config.DSPACE_CREDENTIALS == json.dumps(
        {
            "ir-6": {
                "url": "mock://dspace.edu/rest",
                "user": "test",
                "password": "test",
            },
            "ddc-6": {
                "url": "mock://dspace.edu/rest",
                "user": "test",
                "password": "test",
            },
            "ir-8": {
                "url": "mock://dspace.edu/server/api",
                "user": "test",
                "password": "test",
            },
            "ddc-8": {
                "url": "mock://dspace.edu/server/api",
                "user": "test",
                "password": "test",
            },
        }
    )
    assert config.DSPACE_TIMEOUT == 3.0  # noqa: PLR2004
    assert config.INPUT_QUEUE == "input_queue"
    assert config.LOG_FILTER == "false"
    assert config.LOG_LEVEL == "INFO"
    assert config.SENTRY_DSN == "mock://12345.6789.sentry"
    assert config.SKIP_PROCESSING == "true"
    assert config.SQS_ENDPOINT_URL == "https://sqs.us-east-1.amazonaws.com/"
    assert config.OUTPUT_QUEUES == ["output_queue_1", "output_queue_2"]
