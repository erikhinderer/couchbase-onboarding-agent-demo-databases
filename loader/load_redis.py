import json
import os

import redis


def load(path: str) -> int:
    host = os.environ["REDIS_HOST"]
    port = int(os.environ["REDIS_PORT"])
    username = os.environ["REDIS_USERNAME"]
    password = os.environ["REDIS_PASSWORD"]

    r = redis.Redis(host=host, port=port, username=username, password=password,
                     decode_responses=True, socket_timeout=15)
    r.ping()

    total = 0
    pipe = r.pipeline(transaction=False)
    with open(path, "r") as f:
        for line in f:
            record = json.loads(line)
            pipe.set(f"mockdata:{record['id']}", line.strip())
            total += 1
            if total % 1000 == 0:
                pipe.execute()
                pipe = r.pipeline(transaction=False)
    pipe.execute()

    r.close()
    return total
