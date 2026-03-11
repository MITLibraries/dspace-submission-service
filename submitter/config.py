import json
import logging
import os

logger = logging.getLogger(__name__)


class Config:
    def __init__(self) -> None:
        try:
            self.ENV = os.environ["WORKSPACE"]
        except KeyError:
            logger.error(  # noqa: TRY400
                "Env variable 'WORKSPACE' is required, please set it and try again."
            )
            raise
        self.AWS_REGION_NAME = "us-east-1"
        logger.info(f"Configuring dspace-submission-service for env={self.ENV}")
        self.load_config_variables(self.ENV)

    def load_config_variables(self, env: str) -> None:
        # default to using env vars with defaults
        self.DSPACE_CREDENTIALS = os.getenv("DSS_DSPACE_CREDENTIALS", "{}")
        self.DSPACE_TIMEOUT = float(os.getenv("DSPACE_TIMEOUT", "180.0"))
        self.INPUT_QUEUE = os.getenv("INPUT_QUEUE")
        self.LOG_FILTER = os.getenv("LOG_FILTER", "true").lower()
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
        self.SENTRY_DSN = os.getenv("SENTRY_DSN")
        self.SKIP_PROCESSING = os.getenv("SKIP_PROCESSING", "false").lower()
        self.SQS_ENDPOINT_URL = os.getenv("SQS_ENDPOINT_URL")
        self.OUTPUT_QUEUES = os.getenv("OUTPUT_QUEUES", "output").split(",")

        # if testing environment, override
        if env == "test":
            self.DSPACE_CREDENTIALS = json.dumps(
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
            self.DSPACE_TIMEOUT = 3.0
            self.INPUT_QUEUE = "input_queue"
            self.LOG_FILTER = "true"
            self.LOG_LEVEL = "INFO"
            self.SENTRY_DSN = None
            self.SKIP_PROCESSING = "false"
            self.SQS_ENDPOINT_URL = "https://sqs.us-east-1.amazonaws.com/"
            self.OUTPUT_QUEUES = ["empty_result_queue"]

    @property
    def dspace_credentials(self) -> dict[str, dict[str, str | float | None]]:
        """Return DSpace credentials for supported instances."""
        credentials = json.loads(self.DSPACE_CREDENTIALS)
        return {
            "DSpace@MIT": credentials["ir-6"],
            "IR-8": credentials["ir-8"],
            "DDC-6": credentials["ddc-6"],
            "DDC-8": credentials["ddc-8"],
        }
