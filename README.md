# Mock Database Stack

Docker Compose stack that spins up five database engines and auto-loads each
one with ~100MB of synthetic JSON data on first start:

- MongoDB Enterprise Server (dev/eval license)
- AWS DynamoDB Local
- Redis (official image)
- Apache Cassandra
- Azure Cosmos DB Emulator (Linux, NoSQL API)

## Requirements

- Docker Desktop (or Docker Engine + Compose v2), with at least **8GB RAM and
  4 CPUs** allocated. The Cosmos DB emulator alone recommends ~4GB.
- ~3GB free disk for the five data volumes plus the generated JSON (~500MB in
  `./data`).
- x86_64 or Apple Silicon (arm64) host. MongoDB 5.0+ images require AVX; if
  your CPU doesn't support it, pin an older `mongodb/mongodb-enterprise-server`
  tag in `docker-compose.yml`.

## Quick start

```bash
docker compose up -d --build
```

This starts all five databases, waits for each to report healthy, then runs a
one-shot `loader` container that generates the mock data and bulk-loads it
into every engine. First run takes several minutes (Cassandra and the Cosmos
emulator both need roughly 1-2 minutes just to boot).

Watch progress with:

```bash
docker compose logs -f loader
```

The loader exits (status 0) once all five databases are loaded. Re-running
`docker compose up -d` afterward will reuse the already-generated files in
`./data` and skip regeneration.

## Credentials

| Database | Host:Port | Username | Password | Notes |
|---|---|---|---|---|
| MongoDB Enterprise | localhost:27017 | `demo` | `Couchbase123!` | Root user via `MONGO_INITDB_ROOT_*` |
| Redis | localhost:6379 | `demo` | `Couchbase123!` | ACL user, `default` user disabled |
| Cassandra | localhost:9042 | `demo` | `Couchbase123!` | Created by the loader after bootstrapping with the image's default `cassandra`/`cassandra` superuser |
| DynamoDB Local | localhost:8001 | n/a | n/a | See caveat below |
| Cosmos DB Emulator | localhost:8081 | n/a | n/a | See caveat below |

All values also live in `.env` if you want to change them before first start
(changing them after volumes already exist won't retroactively update
already-created users - wipe the volumes with `docker compose down -v` first).

## Database Names

| Database | Data location |
|MongoDB Enterprise	| database mockdb, collection mock_data |
|DynamoDB Local	| table MockData |
|Redis	keys prefixed | mockdata:<id> (single flat keyspace, DB 0) |
|Cassandra	keyspace | mockdata, table mock_data |
|Cosmos DB Emulator	| database MockDB, container MockData |

### Why Dynamo and Cosmos don't use demo/Couchbase123!

Neither engine has a real username/password auth model:

- **DynamoDB Local** authenticates via the AWS SigV4 signing process, not a
  password. It doesn't validate the credentials at all locally - any
  access key/secret pair satisfies the AWS SDK's credential chain. The
  compose file sets dummy values (`DYNAMODB_ACCESS_KEY_ID=demo`,
  `DYNAMODB_SECRET_ACCESS_KEY=Couchbase123!`) purely so SDKs don't error out;
  they carry no real security meaning.
- **Azure Cosmos DB Emulator** always uses one fixed, publicly documented
  master key (`COSMOS_KEY` in `.env`) - there's no way to set a custom
  username or password for it.

If you need real username/password gating in front of these two, put a proxy
(e.g. an nginx sidecar with basic auth) in front of their ports - ask if you
want that added.

## Connecting

```bash
# MongoDB
mongosh "mongodb://demo:Couchbase123!@localhost:27017/mockdb?authSource=admin"

# Redis
redis-cli -h localhost -p 6379 --user demo --pass 'Couchbase123!' --no-auth-warning

# Cassandra
cqlsh localhost 9042 -u demo -p 'Couchbase123!'

# DynamoDB Local (AWS CLI)
aws dynamodb list-tables --endpoint-url http://localhost:8001 --region us-east-1

# Cosmos DB Emulator Data Explorer
open https://localhost:8081/_explorer/index.html
```

## What data gets loaded

Each database gets its own independently-generated ~100MB JSONL file
(`./data/<db>_data.jsonl`) of synthetic customer/order records (name, email,
company, address, amount, status, tags, metadata) produced with Faker. The
shape is adapted per engine:

- **MongoDB**: inserted as-is into `mockdb.mock_data`.
- **DynamoDB**: `MockData` table, partition key `id`, full record stored in a
  `doc_json` string attribute plus a few top-level attributes.
- **Redis**: each record stored as a JSON string under key `mockdata:<id>`.
- **Cassandra**: `mockdata.mock_data` table, full record stored in a
  `doc_json` text column plus indexed columns for realism.
- **Cosmos DB**: `MockDB` database, `MockData` container, partitioned on
  `/id`, full record as the item body.

Change `MOCK_DATA_SIZE_MB` in `.env` to generate more or less data per
database, then `docker compose down -v && docker compose up -d --build` to
regenerate from scratch.

## Troubleshooting

- **Loader fails on Cosmos with a connection/SSL error**: the emulator can
  take longer than its healthcheck allows on slower machines. Re-run
  `docker compose up -d loader` once `docker compose ps` shows
  `cosmosdb-emulator` as healthy.
- **`mongodb/mongodb-enterprise-server:latest` won't pull**: MongoDB
  periodically prunes old enterprise tags. Check
  https://hub.docker.com/r/mongodb/mongodb-enterprise-server/tags and pin a
  current tag in `docker-compose.yml`.
- **Cassandra healthcheck keeps failing**: first boot creates the
  `system_auth` keyspace, which can take longer on constrained hosts;
  `start_period` is already set to 90s but you can raise it further.
