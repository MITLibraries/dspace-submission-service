import os

import pytest

from submitter.config import Config


def test_config_without_workspace_env_raises_error():
    del os.environ["WORKSPACE"]
    with pytest.raises(KeyError):
        Config()


def test_prod_stage_config_without_ssm_path_env_raises_error():
    os.environ["WORKSPACE"] = "stage"
    os.environ.pop("SSM_PATH", None)
    with pytest.raises(KeyError):
        Config()


def test_prod_stage_config_success(mocked_ssm):
    os.environ["WORKSPACE"] = "stage"
    os.environ["SSM_PATH"] = "/test/example/"
    config = Config()
    assert config.DSPACE_API_URL == "mock://dspace.edu/rest/"
    assert config.DSPACE_USER == "test"
    assert config.DSPACE_PASSWORD == "test"
    assert config.DSPACE_TIMEOUT == 3.0
    assert config.INPUT_QUEUE == "empty_input_queue"
    assert config.LOG_FILTER == "false"
    assert config.LOG_LEVEL == "INFO"
    assert config.SKIP_PROCESSING == "false"
    assert config.SQS_ENDPOINT_URL == "https://sqs.us-east-1.amazonaws.com/"


def test_dev_config_success():
    os.environ["WORKSPACE"] = "dev"
    os.environ.pop("DSPACE_API_URL", None)
    os.environ["DSPACE_USER"] = "dev"
    os.environ.pop("DSPACE_PASSWORD", None)
    os.environ["DSPACE_TIMEOUT"] = "1.0"
    os.environ.pop("DSS_INPUT_QUEUE", None)
    os.environ["DSS_LOG_FILTER"] = "False"
    os.environ["LOG_LEVEL"] = "debug"
    os.environ["SKIP_PROCESSING"] = "True"
    os.environ.pop("SQS_ENDPOINT_URL", None)
    config = Config()
    assert config.DSPACE_API_URL is None
    assert config.DSPACE_USER == "dev"
    assert config.DSPACE_PASSWORD is None
    assert config.DSPACE_TIMEOUT == 1.0
    assert config.INPUT_QUEUE is None
    assert config.LOG_FILTER == "false"
    assert config.LOG_LEVEL == "DEBUG"
    assert config.SKIP_PROCESSING == "true"
    assert config.SQS_ENDPOINT_URL is None
