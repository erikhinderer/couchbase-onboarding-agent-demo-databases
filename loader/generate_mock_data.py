"""
Generates mock JSON data files, one JSON object per line (JSONL), until the
file reaches the requested size. Used to seed every database with the same
shape of synthetic data so the demo is consistent across engines.
"""
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker

fake = Faker()

STATUSES = ["pending", "processing", "shipped", "delivered", "cancelled", "refunded"]
CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD"]
TAG_POOL = [
    "priority", "wholesale", "retail", "loyalty", "first-time", "bulk",
    "gift", "subscription", "b2b", "b2c", "promo", "backorder",
]


def make_record() -> dict:
    created = fake.date_time_between(start_date="-2y", end_date="now", tzinfo=timezone.utc)
    return {
        "id": str(uuid.uuid4()),
        "customer_name": fake.name(),
        "email": fake.email(),
        "company": fake.company(),
        "phone": fake.phone_number(),
        "created_at": created.isoformat(),
        "updated_at": (created + timedelta(days=random.randint(0, 30))).isoformat(),
        "amount": round(random.uniform(5, 5000), 2),
        "currency": random.choice(CURRENCIES),
        "status": random.choice(STATUSES),
        "tags": random.sample(TAG_POOL, k=random.randint(1, 4)),
        "address": {
            "street": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "postal_code": fake.postcode(),
            "country": fake.country_code(),
        },
        "metadata": {
            "source": random.choice(["web", "mobile", "api", "in-store"]),
            "ip_address": fake.ipv4_public(),
            "session_id": str(uuid.uuid4()),
            "notes": fake.sentence(nb_words=12),
        },
    }


def generate_file(path: str, target_mb: float) -> int:
    """Writes JSONL records to `path` until it reaches ~target_mb megabytes.
    Returns the number of records written. Skips generation if the file
    already exists and is already at/near the target size."""
    target_bytes = int(target_mb * 1024 * 1024)

    if os.path.exists(path) and os.path.getsize(path) >= target_bytes * 0.95:
        with open(path, "r") as f:
            count = sum(1 for _ in f)
        print(f"[generate] {path} already exists ({os.path.getsize(path)} bytes, {count} records) - skipping")
        return count

    os.makedirs(os.path.dirname(path), exist_ok=True)
    count = 0
    written = 0
    with open(path, "w") as f:
        while written < target_bytes:
            line = json.dumps(make_record()) + "\n"
            f.write(line)
            written += len(line)
            count += 1
            if count % 50000 == 0:
                print(f"[generate] {path}: {written / (1024*1024):.1f} MB / {target_mb} MB ({count} records)")

    print(f"[generate] {path}: done - {written / (1024*1024):.1f} MB, {count} records")
    return count


if __name__ == "__main__":
    size_mb = float(os.environ.get("MOCK_DATA_SIZE_MB", "100"))
    for name in ["mongo", "dynamodb", "redis", "cassandra", "cosmos"]:
        generate_file(f"/data/{name}_data.jsonl", size_mb)
