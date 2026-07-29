"""
One-shot orchestrator: generates ~100MB (configurable) of mock JSON data per
database, then loads each dataset into its respective engine. Runs once the
five DB containers report healthy (see docker-compose.yml depends_on).

Each database's load step is isolated in a try/except so that a problem with
one engine (e.g. Cosmos emulator still warming up) doesn't stop the others
from loading.
"""
import os
import sys
import time
import traceback

from generate_mock_data import generate_file

import load_mongo
import load_dynamodb
import load_redis
import load_cassandra
import load_cosmos

TARGETS = [
    ("MongoDB Enterprise", "mongo", load_mongo.load),
    ("DynamoDB Local", "dynamodb", load_dynamodb.load),
    ("Redis", "redis", load_redis.load),
    ("Cassandra", "cassandra", load_cassandra.load),
    ("Cosmos DB Emulator", "cosmos", load_cosmos.load),
]


def main():
    size_mb = float(os.environ.get("MOCK_DATA_SIZE_MB", "100"))

    print("=" * 70)
    print(f"Generating ~{size_mb} MB of mock JSON data per database")
    print("=" * 70)
    paths = {}
    for label, name, _ in TARGETS:
        path = f"/data/{name}_data.jsonl"
        generate_file(path, size_mb)
        paths[name] = path

    results = {}
    print()
    print("=" * 70)
    print("Loading data into each database")
    print("=" * 70)
    for label, name, loader_fn in TARGETS:
        print(f"\n--- {label} ---")
        start = time.time()
        try:
            count = loader_fn(paths[name])
            elapsed = time.time() - start
            results[label] = f"OK - {count} records in {elapsed:.1f}s"
            print(f"[{label}] loaded {count} records in {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - start
            results[label] = f"FAILED - {e}"
            print(f"[{label}] FAILED after {elapsed:.1f}s: {e}")
            traceback.print_exc()

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    for label, _, _ in TARGETS:
        print(f"  {label:25s} {results.get(label, 'not run')}")

    if any(v.startswith("FAILED") for v in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
