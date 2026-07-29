import json
import os

from pymongo import MongoClient


def load(path: str) -> int:
    host = os.environ["MONGO_HOST"]
    port = int(os.environ["MONGO_PORT"])
    user = os.environ["MONGO_USERNAME"]
    password = os.environ["MONGO_PASSWORD"]

    client = MongoClient(host=host, port=port, username=user, password=password,
                          authSource="admin", serverSelectionTimeoutMS=15000)
    db = client["mockdb"]
    coll = db["mock_data"]
    coll.drop()

    batch = []
    total = 0
    with open(path, "r") as f:
        for line in f:
            batch.append(json.loads(line))
            if len(batch) >= 1000:
                coll.insert_many(batch, ordered=False)
                total += len(batch)
                batch = []
    if batch:
        coll.insert_many(batch, ordered=False)
        total += len(batch)

    coll.create_index("id", unique=True)
    coll.create_index("email")
    client.close()
    return total
