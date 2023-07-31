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
    assert config.DSPACE_API_URL == "mock://dspace.edu/rest/"
    assert config.DSPACE_USER == "test"
    assert config.DSPACE_PASSWORD == "test"
    assert config.DSPACE_TIMEOUT == 3.0
    assert config.INPUT_QUEUE == "input_queue"
    assert config.LOG_FILTER == "false"
    assert config.LOG_LEVEL == "INFO"
    assert config.SENTRY_DSN == "mock://12345.6789.sentry"
    assert config.SKIP_PROCESSING == "true"
    assert config.SQS_ENDPOINT_URL == "https://sqs.us-east-1.amazonaws.com/"
    assert config.OUTPUT_QUEUES == ["output_queue_1", "output_queue_2"]
