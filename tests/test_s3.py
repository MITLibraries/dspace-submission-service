import os

import boto3
import pytest
from botocore.exceptions import ClientError
from moto.core import set_initial_no_auth_action_count

from submitter.s3 import check_s3_permissions


def test_check_s3_permissions_success(mocked_s3):
    result = check_s3_permissions(["test-bucket"])
    assert (
        result == "S3 list objects and get object permissions confirmed for buckets: "
        "['test-bucket']"
    )


@set_initial_no_auth_action_count(0)
def test_check_s3_permissions_raises_error(mocked_s3, test_aws_user):
    os.environ["AWS_ACCESS_KEY_ID"] = test_aws_user["AccessKeyId"]
    os.environ["AWS_SECRET_ACCESS_KEY"] = test_aws_user["SecretAccessKey"]
    boto3.setup_default_session()
    with pytest.raises(ClientError) as e:
        check_s3_permissions(["test-bucket"])
    assert (
        "An error occurred (AccessDenied) when calling the GetObject operation: Access "
        "Denied" in str(e.value)
    )
