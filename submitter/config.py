import logging
import os

from submitter.ssm import SSM

logger = logging.getLogger(__name__)


class Config:
    def __init__(self):
        try:
            self.ENV = os.environ["WORKSPACE"]
        except KeyError as e:
            print("Env variable 'WORKSPACE' is required, please set it and try again.")
            raise e
        self.AWS_REGION_NAME = "us-east-1"
        logger.info(
            "Configuring dspace-submission-service for current env: %s", self.ENV
        )
        self.load_config_variables(self.ENV)

    def load_config_variables(self, env: str):
        if env in ["prod", "stage"]:
            try:
                self.SSM_PATH = os.environ["SSM_PATH"]
            except KeyError as e:
                print(
                    f"Env variable 'SSM_PATH' is required in the {env} environment, "
                    "please set it and try again."
                )
                raise e
            ssm = SSM()
            self.DSPACE_API_URL = ssm.get_parameter_value(
                self.SSM_PATH + "dspace_api_url"
            )
            self.DSPACE_USER = ssm.get_parameter_value(self.SSM_PATH + "dspace_user")
            self.DSPACE_PASSWORD = ssm.get_parameter_value(
                self.SSM_PATH + "dspace_password"
            )
            self.DSPACE_TIMEOUT = float(
                ssm.get_parameter_value(self.SSM_PATH + "dspace_timeout")
            )
            self.INPUT_QUEUE = ssm.get_parameter_value(
                self.SSM_PATH + "SQS_dss_input_queue"
            )
            self.LOG_FILTER = ssm.get_parameter_value(
                self.SSM_PATH + "dss_log_filter"
            ).lower()
            self.LOG_LEVEL = ssm.get_parameter_value(
                self.SSM_PATH + "dss_log_level"
            ).upper()
            self.SKIP_PROCESSING = "false"
            self.SQS_ENDPOINT_URL = "https://sqs.us-east-1.amazonaws.com/"
        elif env == "test":
            self.DSPACE_API_URL = "mock://dspace.edu/rest/"
            self.DSPACE_USER = "test"
            self.DSPACE_PASSWORD = "test"  # nosec
            self.DSPACE_TIMEOUT = 3.0
            self.INPUT_QUEUE = "test_queue_with_messages"
            self.LOG_FILTER = "true"
            self.LOG_LEVEL = os.getenv("DSS_LOG_LEVEL", "INFO").upper()
            self.SKIP_PROCESSING = "false"
            self.SQS_ENDPOINT_URL = "https://sqs.us-east-1.amazonaws.com/"
        else:
            self.DSPACE_API_URL = os.getenv("DSPACE_API_URL")
            self.DSPACE_USER = os.getenv("DSPACE_USER")
            self.DSPACE_PASSWORD = os.getenv("DSPACE_PASSWORD")
            self.DSPACE_TIMEOUT = float(os.getenv("DSPACE_TIMEOUT", "120.0"))
            self.INPUT_QUEUE = os.getenv("DSS_INPUT_QUEUE")
            self.LOG_FILTER = os.getenv("DSS_LOG_FILTER", "true").lower()
            self.LOG_LEVEL = os.getenv("DSS_LOG_LEVEL", "INFO").upper()
            self.SKIP_PROCESSING = os.environ.get("SKIP_PROCESSING", "false").lower()
            self.SQS_ENDPOINT_URL = os.environ.get("SQS_ENDPOINT_URL")
