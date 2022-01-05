import pytest

from submitter.ssm import SSM

# import os
# import boto3
# from botocore.exceptions import ClientError
# from moto.core import set_initial_no_auth_action_count


def test_get_parameter_value_success(mocked_ssm):
    ssm = SSM()
    assert ssm.get_parameter_value("/test/example/dspace_user") == "test"


def test_get_parameter_value_raises_error_with_parameter_name_if_not_found(mocked_ssm):
    ssm = SSM()
    with pytest.raises(Exception) as e:
        ssm.get_parameter_value("/test/example/nothinghere")
    assert str(e.value) == "Parameter '/test/example/nothinghere' not found"


def test_check_permissions_success(mocked_ssm):
    ssm = SSM()
    assert (
        ssm.check_permissions("/test/example/")
        == "SSM permissions confirmed for path '/test/example/'"
    )


# This test raises a weird error that seems like a moto issue. Leaving it here but
# commented out for now
# @set_initial_no_auth_action_count(0)
# def test_check_permissions_raises_error_if_no_permission(mocked_ssm, test_aws_user):
#     os.environ["AWS_ACCESS_KEY_ID"] = test_aws_user["AccessKeyId"]
#     os.environ["AWS_SECRET_ACCESS_KEY"] = test_aws_user["SecretAccessKey"]
#     boto3.setup_default_session()
#     ssm = SSM()
#     with pytest.raises(ClientError) as e:
#         ssm.check_permissions("/test/example/")
#     assert "Access Denied" in str(e.value)
