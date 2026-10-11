from __future__ import annotations

import os
import uuid

import boto3
import pytest

ENDPOINT = os.environ.get("THREADIT_AWS_ENDPOINT_URL", "http://localhost:4566")
REGION = "us-east-1"


def _client():
    return boto3.client("dynamodb", endpoint_url=ENDPOINT, region_name=REGION)


@pytest.fixture()
def table_name():
    name = f"threadit_it_{uuid.uuid4().hex[:8]}"
    c = _client()
    c.create_table(
        TableName=name,
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
            {"AttributeName": "GSI2PK", "AttributeType": "S"},
            {"AttributeName": "GSI2SK", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "GSI2",
                "KeySchema": [
                    {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    yield name
    c.delete_table(TableName=name)


@pytest.fixture()
def table(table_name):
    resource = boto3.resource("dynamodb", endpoint_url=ENDPOINT, region_name=REGION)
    return resource.Table(table_name)
