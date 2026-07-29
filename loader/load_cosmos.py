import json
import os
import time

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceExistsError, CosmosHttpResponseError, ServiceRequestError


def load(path: str) -> int:
    endpoint = os.environ["COSMOS_ENDPOINT"]
    key = os.environ["COSMOS_KEY"]

    # The emulator's gateway can accept TCP connections slightly before its
    # HTTP/TLS layer is actually ready to serve requests, so the docker
    # healthcheck passing doesn't guarantee the SDK call below will succeed
    # on the first try. Retry with backoff instead of failing the whole run.
    max_attempts = 10
    db = None
    container = None
    for attempt in range(1, max_attempts + 1):
        try:
            client = CosmosClient(endpoint, credential=key, connection_verify=False)
            db = client.create_database_if_not_exists(id="MockDB")
            container = db.create_container_if_not_exists(
                id="MockData",
                partition_key=PartitionKey(path="/id"),
                offer_throughput=400,
            )
            break
        except (CosmosHttpResponseError, ServiceRequestError, ConnectionError) as e:
            if attempt == max_attempts:
                raise
            wait = min(5 * attempt, 30)
            print(f"[cosmos] not ready yet (attempt {attempt}/{max_attempts}: {e}); retrying in {wait}s")
            time.sleep(wait)

    total = 0
    with open(path, "r") as f:
        for line in f:
            record = json.loads(line)
            try:
                container.upsert_item(record)
            except CosmosResourceExistsError:
                pass
            total += 1

    return total
