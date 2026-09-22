import json
import logging
import os
from typing import Literal

import sentry_sdk

logger = logging.getLogger(__name__)


class Config:
    REQUIRED_ENV_VARS = (
        "WORKSPACE",
        "DIGCOLL_RW_API_CREDENTIALS_JSON",
        "OPENSCHOL_RW_API_CREDENTIALS_JSON",
        "INPUT_QUEUE",
        "OUTPUT_QUEUES",
    )
    OPTIONAL_ENV_VARS = (
        "SENTRY_DSN",
        "DSPACE_TIMEOUT",
        "SKIP_PROCESSING",
        "SQS_ENDPOINT_URL",
        "WARNING_ONLY_LOGGERS",
    )

    @property
    def workspace(self) -> str:
        return os.getenv("WORKSPACE", "dev")

    @property
    def digcoll_rw_api_credentials_json(self) -> dict:
        value = os.getenv("DIGCOLL_RW_API_CREDENTIALS_JSON")
        if not value:
            raise ValueError("Env var 'DIGCOLL_RW_API_CREDENTIALS_JSON' must be defined")
        return json.loads(value)

    @property
    def openschol_rw_api_credentials_json(self) -> dict:
        value = os.getenv("OPENSCHOL_RW_API_CREDENTIALS_JSON")
        if not value:
            raise ValueError(
                "Env var 'OPENSCHOL_RW_API_CREDENTIALS_JSON' must be defined"
            )
        return json.loads(value)

    @property
    def input_queue(self) -> str:
        value = os.getenv("INPUT_QUEUE")
        if not value:
            raise ValueError("Env var 'INPUT_QUEUE' must be defined")
        return value

    @property
    def output_queues(self) -> list[str]:
        value = os.getenv("OUTPUT_QUEUES")
        if not value:
            raise ValueError("Env var 'OUTPUT_QUEUES' must be defined")
        return value.split(",")

    @property
    def sentry_dsn(self) -> str | None:
        dsn = os.getenv("SENTRY_DSN")
        if dsn and dsn.strip().lower() != "none":
            return dsn
        return None

    @property
    def dspace_timeout(self) -> float:
        value = os.getenv("DSPACE_TIMEOUT", "180")
        return float(value)

    @property
    def skip_processing(self) -> bool:
        value = os.getenv("SKIP_PROCESSING", "false")
        return value.lower() == "true"

    @property
    def sqs_endpoint_url(self) -> str | None:
        return os.getenv("SQS_ENDPOINT_URL")

    @property
    def warning_only_loggers(self) -> list | None:
        value = os.getenv("WARNING_ONLY_LOGGERS", "botocore,boto3,smart_open,urllib3")
        try:
            loggers = value.split(",")
        except AttributeError:
            return []
        return loggers

    def get_dspace_credentials(
        self, submission_system: Literal["DSpace@MIT", "IR-8", "DDC-8"]
    ) -> dict:
        """Get parsed dspace credentials."""
        if submission_system in ("DSpace@MIT", "IR-8"):
            return self.openschol_rw_api_credentials_json
        if submission_system == "DDC-8":
            return self.digcoll_rw_api_credentials_json

        raise ValueError(
            f"'submission_system' should be one of ['DSpace@MIT','IR-8', 'DDC-8'], got '{submission_system}'"  # noqa: E501
        )


def configure_logger(
    root_logger: logging.Logger,
    *,
    verbose: bool = False,
    warning_only_loggers: list | None = None,
) -> str:
    """Configure application via passed application root logger.

    If verbose=True, 3rd party libraries can be quite chatty.  For convenience, they can
    be set to WARNING level by either passing a comma seperated list of logger names to
    'warning_only_loggers' or by setting the env var WARNING_ONLY_LOGGERS.
    """
    if verbose:
        root_logger.setLevel(logging.DEBUG)
        logging_format = (
            "%(asctime)s %(levelname)s %(name)s.%(funcName)s() "
            "line %(lineno)d: %(message)s"
        )
    else:
        root_logger.setLevel(logging.INFO)
        logging_format = "%(asctime)s %(levelname)s %(name)s.%(funcName)s(): %(message)s"

    if warning_only_loggers:
        for name in warning_only_loggers:
            logging.getLogger(name).setLevel(logging.WARNING)

    for handler in root_logger.handlers:
        handler.setFormatter(logging.Formatter(logging_format))

    return (
        f"Logger '{root_logger.name}' configured with level="
        f"{logging.getLevelName(root_logger.getEffectiveLevel())}"
    )


def configure_sentry() -> None:
    env = os.getenv("WORKSPACE")
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn and sentry_dsn.lower() != "none":
        sentry_sdk.init(sentry_dsn, environment=env)
        logger.info(f"Sentry DSN found, exceptions will be sent to Sentry with env={env}")
    else:
        logger.info("No Sentry DSN found, exceptions will not be sent to Sentry")
