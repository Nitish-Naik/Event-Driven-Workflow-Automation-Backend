# Event-Driven Workflow Automation Backend

A production-oriented backend for turning Sentry incidents into automated workflow actions.

**Core flow:**

```text
Sentry
  ↓ Service Hook
FastAPI webhook
  ↓ validate + normalize
MongoDB + Redis
  ↓
Worker
  ↓
Workflow Engine
  ├── Normalize event
  ├── AI analysis
  ├── Condition
  └── Slack notification
```

MongoDB is the durable source of truth. Redis is used for the transient event queue. Workflow runs track status, attempts, workflow version, errors, and outputs.

## Quick Start

### Prerequisites

- Python 3.11+
- Docker Desktop
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Nitish-Naik/Event-Driven Workflow Automation Backend.git
cd Event-Driven Workflow Automation Backend/backend
```

### 2. Create the environment file

```bash
cp .env.example .env
```

On Windows PowerShell, use:

```powershell
Copy-Item .env.example .env
```

For a basic local run, MongoDB and Redis are enough. Sentry and Slack credentials are only required when testing those external integrations.

**Never commit `.env` or real credentials.**

### 3. Start MongoDB and Redis

From the repository root:

```bash
docker compose up -d
```

The compose file starts:

- MongoDB on `localhost:27017`
- Redis on `localhost:6379`

### 4. Create a Python environment

From `backend/`:

```bash
python -m venv .venv
```

Activate it:

**macOS/Linux:**

```bash
source .venv/bin/activate
```

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 5. Start the API

From `backend/`:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

Verify the API and its database/Redis dependencies:

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok","environment":"development"}
```

### 6. Start the worker

Open a second terminal, activate the same virtual environment, and from `backend/` run:

```bash
python -m app.worker.event_worker
```

You should see:

```text
Worker runner started
```

## Run the tests

From `backend/`:

```bash
pytest -q
```

The current repository state has **255 passing tests**.

## Test a workflow through the API

The backend exposes workflow CRUD/versioning, activation, and a workflow test endpoint.

List workflows:

```bash
curl http://localhost:8000/workflows
```

A workflow can also be tested without sending a real Sentry event using:

```text
POST /workflows/{workflow_id}/versions/{version}/test
```

Example request body:

```json
{
  "event_type": "event.created",
  "payload": {
    "message": "Test incident",
    "level": "error"
  }
}
```

## Real Sentry integration

The production-style integration uses a Sentry Service Hook:

```text
Sentry event
  ↓
Sentry Service Hook
  ↓
POST /webhooks/sentry
  ↓
Signature verification
  ↓
Event normalization
  ↓
MongoDB persistence
  ↓
Redis queue
  ↓
Worker
  ↓
Workflow execution
  ↓
Slack
```

Configure the Sentry values in `backend/.env`:

```env
SENTRY_BASE_URL=https://sentry.io

SENTRY_CLIENT_SECRET=
SENTRY_DSN=
SENTRY_ORG_SLUG=
SENTRY_AUTH_TOKEN=
SENTRY_WEBHOOK_SECRET=
SLACK_BOT_TOKEN=
SLACK_CHANNEL_ID=
SENTRY_HOOK_ID=
SENTRY_WEBHOOK_URL=
```

Configure the Slack values if using Slack notifications:

```env
SLACK_BOT_TOKEN=
SLACK_CHANNEL_ID=
```

The webhook endpoint is:

```text
POST /webhooks/sentry
```

The endpoint verifies the `x-servicehook-signature` header when a webhook secret is configured.

For a real external integration, the Sentry Service Hook URL must be able to reach the running API. A localhost URL is not reachable from Sentry; use an appropriately secured public endpoint or tunnel for development.

## Reliability and failure handling

### Idempotency

Workflow executions use an execution key based on the event, workflow, and workflow version. This prevents duplicate workflow runs when the same event is delivered more than once or concurrent workers race to create the same run.

### Retry policy

Transient failures are retryable, including:

- HTTP 429
- HTTP 5xx
- request timeouts

Retries use exponential backoff with jitter. Permanent client errors are not retried.

The retry behavior is covered by an integration-level test that injects a failing Slack dependency, verifies the real worker retry path, and then verifies successful completion on the second attempt.

### Dead-letter handling

A run moves through the following lifecycle when processing fails:

```text
FAILED → RETRYING → PROCESSING
                    ↓
             success → COMPLETED

             retry limit → DEAD_LETTER
```

## Node abstraction

The workflow engine is built around reusable nodes. The executor handles workflow traversal and execution coordination, while individual nodes and integrations encapsulate their own behavior.

This keeps the core workflow engine independent of specific external providers such as Slack and makes new workflow capabilities easier to add and test.

## Workflow model

A workflow is versioned and consists of nodes and directed edges. Nodes can represent triggers, transformations, AI analysis, conditions, and integrations.

Example execution path:

```text
Sentry Trigger
     ↓
Normalize Event
     ↓
AI Analysis
     ↓
Condition
     ↓
Slack
```

Each workflow run records the workflow version that actually executed.

## Project structure

```text
VectorShift/
├── backend/
│   ├── app/
│   │   ├── db/              # MongoDB, Redis, repositories
│   │   ├── execution/       # Workflow execution engine and registry
│   │   ├── integrations/    # Sentry, Slack and integration tools
│   │   ├── routers/         # HTTP API and webhook endpoints
│   │   ├── schemas/         # Pydantic domain/API schemas
│   │   ├── services/        # Workflow/domain services
│   │   └── worker/          # Redis-backed event worker
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── docker-compose.yml
└── README.md
```

## Key API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Health check for API, MongoDB and Redis |
| `GET` | `/workflows` | List workflows |
| `POST` | `/workflows` | Create workflow |
| `GET` | `/workflows/{id}/versions/{version}` | Get workflow version |
| `PUT` | `/workflows/{id}/versions/{version}` | Update workflow version |
| `POST` | `/workflows/{id}/versions/{version}/activate` | Activate workflow version |
| `POST` | `/workflows/{id}/versions/{version}/deactivate` | Deactivate workflow version |
| `POST` | `/workflows/{id}/versions/{version}/test` | Execute a workflow test |
| `POST` | `/webhooks/sentry` | Receive Sentry Service Hook events |

## Design decisions

- **FastAPI:** lightweight async HTTP API and webhook handling.
- **MongoDB:** durable event and workflow-run persistence.
- **Redis:** transient queue and worker coordination.
- **Worker:** keeps webhook processing asynchronous and decoupled from workflow execution.
- **Workflow versioning:** makes executions reproducible and auditable.
- **Provider abstractions:** Sentry, Slack, and AI integrations are isolated behind interfaces/registries so external dependencies can be tested independently.

## Development notes

The current implementation is intentionally a focused backend system rather than a distributed Kafka/Kubernetes deployment. The Redis queue uses a reliable-list pattern with a processing list; it is not intended to claim full broker-level visibility-timeout semantics.

The condition node evaluates its configured predicate. The current executor does not use a false condition as a graph-level branch/gate, so the demo workflow uses a true condition on its successful path.

## Verification

The backend has been verified end-to-end with a real Sentry event:

```text
Real Sentry event
  → Sentry Service Hook
  → FastAPI webhook
  → MongoDB + Redis
  → Worker
  → Workflow
  → Slack API 200
  → COMPLETED
```
