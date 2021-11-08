import logging
import os

from submitter.ssm import SSM

logger = logging.getLogger(__name__)

env = os.getenv("WORKSPACE")
ssm_path = os.getenv("SSM_PATH")

logger.info("Configuring dspace-submission-service for current env: %s", env)

ssm = SSM()

AWS_REGION_NAME = "us-east-1"

if env == "stage" or env == "prod":
    DSPACE_API_URL = ssm.get_parameter_value(ssm_path + "dspace_api_url")
    DSPACE_USER = ssm.get_parameter_value(ssm_path + "dspace_user")
    DSPACE_PASSWORD = ssm.get_parameter_value(ssm_path + "dspace_password")
    DSPACE_TIMEOUT = float(ssm.get_parameter_value(ssm_path + "dspace_timeout"))
    INPUT_QUEUE = ssm.get_parameter_value(ssm_path + "SQS_dss_input_queue")
    SKIP_PROCESSING = "false"
    SQS_ENDPOINT_URL = "https://sqs.us-east-1.amazonaws.com/"
elif env == "test":
    DSPACE_API_URL = "mock://dspace.edu/rest/"
    DSPACE_USER = "test"
    DSPACE_PASSWORD = "test"  # nosec
    DSPACE_TIMEOUT = 3.0
    INPUT_QUEUE = "test_queue_with_messages"
    SKIP_PROCESSING = "false"
    SQS_ENDPOINT_URL = "https://sqs.us-east-1.amazonaws.com/"
else:
    DSPACE_API_URL = os.getenv("DSPACE_API_URL")
    DSPACE_USER = os.getenv("DSPACE_USER")
    DSPACE_PASSWORD = os.getenv("DSPACE_PASSWORD")
    DSPACE_TIMEOUT = float(os.getenv("DSPACE_TIMEOUT", "120.0"))
    INPUT_QUEUE = os.getenv("DSS_INPUT_QUEUE")
    SKIP_PROCESSING = os.environ.get("SKIP_PROCESSING", "false")
    SQS_ENDPOINT_URL = os.environ.get("SQS_ENDPOINT_URL")
