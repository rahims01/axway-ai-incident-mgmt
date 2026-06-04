# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Axway SecureTransport AI AIOps Platform** — automated incident detection, root cause analysis, and autonomous remediation for Axway SecureTransport MFT environments.

Full aspirational architecture blueprint: [SIMPLE-ARCHITECTURE.md](SIMPLE-ARCHITECTURE.md)

## Business Context

Axway SecureTransport is the enterprise MFT platform. Clients transfer files via SFTP (RSA/ECDSA keys), AS2, HTTPS (SSL certs), and FTPS. High incident volume around: expired certs, SSH key mismatches, AS2 MDN failures, cipher incompatibilities, stuck queues, JVM exhaustion.

## Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env   # edit as needed

# Run dev server (hot reload)
uvicorn api.main:app --reload

# Docker (dev — mounts source for hot reload, SQLite on ./data/)
docker compose up

# Docker (production — multi-stage build, non-root user, no source mount)
docker compose -f docker-compose.prod.yml up -d
# Requires .env.prod (copy from .env.example). Uses Dockerfile.prod.
```

Dashboard available at `http://localhost:8000`. Swagger UI at `http://localhost:8000/docs`.

Both Axway and LLM default to **mock mode** — the app is fully functional without any API keys. Set `AZURE_OPENAI_API_KEY` in `.env` to enable real AI analysis. Set `MOCK_AXWAY=false` with real Axway credentials to connect to a live instance.

## What Is Actually Built

The current implementation is a working FastAPI + SQLite application, **not** the full multi-agent LangGraph stack described in the architecture docs. The stack that exists today:

| Component | What it does |
|---|---|
| `api/main.py` | FastAPI app — all REST endpoints and webhook receiver |
| `agent/agents.py` | Proactive check runner + LLM-based incident analyzer + auto-fix dispatcher |
| `checks/__init__.py` | Six health check functions collected in `ALL_CHECKS` |
| `llm/client.py` | Azure OpenAI (gpt-4o) wrapper with realistic mock fallback per incident category |
| `collector/axway_client.py` | Axway Admin REST API client; `MOCK_AXWAY=true` returns deterministic demo data |
| `collector/scheduler.py` | APScheduler background job — runs all checks every 5 minutes |
| `models/incident.py` | SQLAlchemy `Incident` ORM model + Pydantic I/O schemas |
| `config/settings.py` | Pydantic-settings — reads `.env`, exposes typed `settings` singleton |
| `actions/axway_actions.py` | Mutating actions (cert renew, known_hosts update, retry transfers, restart service) |
| `notifications/notifier.py` | Slack / Teams / ServiceNow alert fanout |
| `agent/prompts.py` | System prompts for incident analysis and chat |

**Database:** SQLite by default (`axway_aiops.db`). Switch to PostgreSQL by changing `DATABASE_URL` in `.env`.

## Incident Lifecycle

```
NEW → ANALYZING → NEW (with RCA attached) → REMEDIATING → RESOLVED / ESCALATED
```

Incidents are created by proactive checks (via scheduler) or by the `/api/webhooks/alert` endpoint. Deduplication uses a `fingerprint` (MD5 of `check_name:category:partner_id`) — only one open incident per fingerprint at a time.

## Proactive Checks

Six checks in `checks/__init__.py`, all registered in `ALL_CHECKS`:

| Check function | What it detects |
|---|---|
| `check_cert_expiry` | TLS certs expiring within `CERT_EXPIRY_WARN_DAYS` |
| `check_transfer_failures` | ≥ `FAILURE_RATE_THRESHOLD` failures in the last 5 min per partner |
| `check_partner_silence` | Partner silent longer than `expected_transfer_interval_hours` |
| `check_ssh_keys` | DSA keys, RSA < 2048 bits, weak/aged keys |
| `check_queue_depth` | Queue depth above `QUEUE_DEPTH_WARN` threshold |
| `check_jvm_health` | JVM heap above `JVM_HEAP_WARN_PCT` or disk above `DISK_WARN_PCT` |

## Auto-Fix Actions

Dispatched by `actions/axway_actions.dispatch_action()`. Every action captures pre-state and runs a post-check. In mock mode these log what they would do and return success.

| `auto_fix_action` string | What it does |
|---|---|
| `UPDATE_KNOWN_HOSTS` | Updates SSH known_hosts fingerprint for a partner |
| `RENEW_CERTIFICATE` | Imports a new cert via Axway Admin API |
| `RETRY_TRANSFER` / `RETRY_QUEUED_TRANSFERS` | Retries up to 10 failed transfers per run |
| `RESTART_TRANSFER_MANAGER` | Restarts the Axway Transfer Manager service |
| `CLEAR_QUEUE` | Retries (does not discard) queued items |

Auto-fix only runs when `incident.auto_fixable=True` and `incident.auto_fix_action` is set. Confidence threshold for autonomous action is controlled by `AUTO_FIX_CONFIDENCE_THRESHOLD` (default 85).

## Key Design Decisions

- **Mock-first design** — both Axway API and LLM have realistic mock modes so the full UI/workflow can be demonstrated without infrastructure
- **Confidence threshold 85** — LLM analysis below this falls back to human escalation; set in `config/settings.py` as `auto_fix_confidence_threshold`
- **P1/P2 human approval** — `AWAITING_APPROVAL` status and `notifications/notifier.py::request_approval()` are scaffolded but nothing calls `request_approval()` yet; mutating actions run immediately in mock mode
- **Rollback intent on every mutating action** — pre-state capture is scaffolded in `actions/axway_actions.py`; real rollback calls are marked `PLACEHOLDER` for production wiring
- **LLM analysis fields vs. DB fields** — `llm/schemas.py::IncidentAnalysis` returns `evidence`, `safety_notes`, `escalate_if`, and `estimated_fix_minutes` from the LLM, but only `root_cause`, `confidence`, `fix_steps`, `auto_fixable`, and `auto_fix_action` are persisted to the `Incident` table; the rest are discarded after the analysis call
- **ServiceNow integration** — `notifications/notifier.py::create_servicenow_ticket()` is a fully-commented placeholder; it logs intent but makes no API call even when `servicenow_enabled=True`

## Axway Admin API

Base URL: `settings.axway_admin_url` + `/api/v1.4`. Key endpoints used:
- `GET /accounts` — list partners
- `GET /certificates` — list certs with expiry metadata
- `GET /transfers` — filtered by partner/status/time window
- `PUT /accounts/{id}/sshKnownHosts` — update SSH fingerprint
- `POST /certificates/import` — import renewed cert
- `POST /services/{name}/restart` — restart a service

## Aspirational Architecture (Future Phases)

The planned full stack (not yet built): Kafka event bus → Apache Flink stream processing → LangGraph multi-agent orchestration (Triage, RCA, Remediation, Knowledge, Predictive, Compliance agents) → OPA policy gate → Temporal.io durable workflows → Qdrant vector DB for RAG → on-prem Llama 3.3 70B for raw log analysis → HashiCorp Vault for secrets/PKI.

- **Phase 1 (M1–3):** Log collection, Kafka pipeline, Triage Agent, Knowledge Base, ServiceNow integration
- **Phase 2 (M4–6):** RCA Agent, Remediation Agent (P3/P4 auto), Policy Engine, Predictive alerts
- **Phase 3 (M7–9):** Full autonomy for known patterns, cert renewal, key rotation, Compliance Agent
- **Phase 4 (M10–12):** Partner portal, capacity planning, change impact prediction
