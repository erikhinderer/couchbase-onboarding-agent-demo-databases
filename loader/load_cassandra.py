import json
import os

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent_with_args


def load(path: str) -> int:
    host = os.environ["CASSANDRA_HOST"]
    port = int(os.environ["CASSANDRA_PORT"])
    bootstrap_user = os.environ["CASSANDRA_BOOTSTRAP_USERNAME"]
    bootstrap_pass = os.environ["CASSANDRA_BOOTSTRAP_PASSWORD"]
    demo_user = os.environ["CASSANDRA_DEMO_USERNAME"]
    demo_pass = os.environ["CASSANDRA_DEMO_PASSWORD"]

    # First connect with the image's default bootstrap superuser (cassandra/cassandra)
    # and create the demo role requested by the user.
    auth = PlainTextAuthProvider(username=bootstrap_user, password=bootstrap_pass)
    cluster = Cluster([host], port=port, auth_provider=auth, connect_timeout=20)
    session = cluster.connect()

    session.execute(f"""
        CREATE ROLE IF NOT EXISTS {demo_user}
        WITH PASSWORD = '{demo_pass}' AND LOGIN = true AND SUPERUSER = true
    """)

    session.execute("""
        CREATE KEYSPACE IF NOT EXISTS mockdata
        WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
    """)
    session.execute("""
        CREATE TABLE IF NOT EXISTS mockdata.mock_data (
            id uuid PRIMARY KEY,
            customer_name text,
            email text,
            status text,
            amount decimal,
            created_at timestamp,
            doc_json text
        )
    """)

    insert_stmt = session.prepare("""
        INSERT INTO mockdata.mock_data (id, customer_name, email, status, amount, created_at, doc_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """)

    from datetime import datetime
    from decimal import Decimal
    import uuid as uuidlib

    params = []
    total = 0
    with open(path, "r") as f:
        for line in f:
            record = json.loads(line)
            params.append((
                uuidlib.UUID(record["id"]),
                record["customer_name"],
                record["email"],
                record["status"],
                Decimal(str(record["amount"])),
                datetime.fromisoformat(record["created_at"]),
                line.strip(),
            ))
            if len(params) >= 500:
                execute_concurrent_with_args(session, insert_stmt, params, concurrency=50)
                total += len(params)
                params = []
    if params:
        execute_concurrent_with_args(session, insert_stmt, params, concurrency=50)
        total += len(params)

    cluster.shutdown()
    return total
