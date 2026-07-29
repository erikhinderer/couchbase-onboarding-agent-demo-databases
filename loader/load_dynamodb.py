import json
import os

import boto3
from botocore.exceptions import ClientError


def load(path: str) -> int:
    endpoint = os.environ["DYNAMODB_ENDPOINT"]
    access_key = os.environ["DYNAMODB_ACCESS_KEY_ID"]
    secret_key = os.environ["DYNAMODB_SECRET_ACCESS_KEY"]

    resource = boto3.resource(
        "dynamodb",
        endpoint_url=endpoint,
        region_name="us-east-1",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    client = resource.meta.client

    table_name = "MockData"
    try:
        client.describe_table(TableName=table_name)
        resource.Table(table_name).delete()
        client.get_waiter("table_not_exists").wait(TableName=table_name)
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise

    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    client.get_waiter("table_exists").wait(TableName=table_name)

    table = resource.Table(table_name)
    total = 0
    with open(path, "r") as f, table.batch_writer() as batch:
        for line in f:
            record = json.loads(line)
            item = {
                "id": record["id"],
                "customer_name": record["customer_name"],
                "email": record["email"],
                "status": record["status"],
                "amount": str(record["amount"]),
                "doc_json": json.dumps(record),
            }
            batch.put_item(Item=item)
            total += 1

    return total
