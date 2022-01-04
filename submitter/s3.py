import logging
from typing import List

import boto3

logger = logging.getLogger(__name__)


def check_s3_permissions(buckets: List[str]) -> str:
    """Checks S3 ListObjectV2 and GetObject permissions for all buckets provided in the
    passed list. If either command is not allowed for any of the provided buckets,
    raises an Access Denied bocotore client error.
    """
    s3 = boto3.client("s3")
    bucket_names = []
    for bucket in buckets:
        response = s3.list_objects_v2(Bucket=bucket, MaxKeys=1)
        logger.debug(f"Successfully listed objects in bucket '{bucket}'")
        for object in response["Contents"]:
            s3.get_object(Bucket=bucket, Key=object["Key"])
            bucket_names.append(bucket)
            logger.debug(
                f"Successfully retrieved object '{object['Key']}' from bucket "
                f"'{bucket}'"
            )
    return (
        "S3 list objects and get object permissions confirmed for buckets: "
        f"{bucket_names}"
    )
