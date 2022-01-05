import logging

from boto3 import client
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SSM:
    """An SSM class that provides a generic boto3 SSM client with specific SSM
    functionality necessary for dspace submission service"""

    def __init__(self):
        self.client = client("ssm", region_name="us-east-1")

    def get_parameter_value(self, parameter_key):
        """Get parameter value based on the specified key."""
        try:
            parameter_object = self.client.get_parameter(
                Name=parameter_key, WithDecryption=True
            )
        except ClientError as e:
            if "ParameterNotFound" in str(e):
                raise Exception(f"Parameter '{parameter_key}' not found") from e
            raise e
        parameter_value = parameter_object["Parameter"]["Value"]
        return parameter_value

    def check_permissions(self, ssm_path: str) -> str:
        """Check whether we can retrieve an encrypted ssm parameter.
        Raises an exception if we can't retrieve the parameter at all OR if the
        parameter is retrieved but the value can't be decrypted.
        """
        decrypted_parameter = self.get_parameter_value(ssm_path + "secure")
        if decrypted_parameter != "true":
            raise (
                "Was not able to successfully retrieve encrypted SSM parameter "
                f"{decrypted_parameter}"
            )
        return f"SSM permissions confirmed for path '{ssm_path}'"
