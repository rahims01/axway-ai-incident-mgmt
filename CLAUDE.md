# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Axway SecureTransport AI AIOps Platform** — a multi-agent AIOps system for automated incident detection, root cause analysis, and autonomous remediation for Axway SecureTransport Managed File Transfer (MFT) environments.

Full architecture blueprint: [ARCHITECTURE.md](ARCHITECTURE.md)

## Business Context

Axway SecureTransport is the enterprise MFT platform. Clients transfer files via SFTP (RSA/ECDSA keys), AS2, HTTPS (SSL certs), and FTPS. High incident volume around: expired certs, SSH key mismatches, AS2 MDN failures, cipher incompatibilities, stuck queues, JVM exhaustion.

## Architecture Overview

Six cooperating AI agents orchestrated by LangGraph, governed by OPA policy engine, grounded in a RAG knowledge layer:

| Agent | Purpose |
|---|---|
| Triage Agent | Normalize alerts → structured incidents with severity + probable cause |
| RCA Agent | Deep log analysis → root cause with evidence + confidence score |
| Remediation Agent | Execute approved fixes against Axway API + infra |
| Knowledge Agent | Conversational Q&A over runbooks, docs, historical tickets |
| Predictive Agent | Cert expiry, SLA breach, partner health forecasting |
| Compliance Agent | Cipher/key/cert inventory, audit evidence generation |

**Event bus:** Kafka — all inter-component communication  
**Stream processing:** Apache Flink — log parsing, correlation, deduplication  
**Workflow engine:** Temporal.io — durable long-running remediation workflows  
**Vector DB:** Qdrant — RAG knowledge retrieval  
**Policy engine:** OPA (Rego) — gates all autonomous remediation actions  
**LLM routing:** Claude Haiku → triage/summarization; Claude Sonnet → RCA/Q&A; Claude Opus → P1/P2 remediation planning; on-prem Llama 3.3 70B for sensitive log analysis  
**Secret management:** HashiCorp Vault — dynamic Axway API credentials, PKI for cert renewal, SSH signing  

## Key Design Decisions

- **Log data never goes to cloud LLM APIs** — on-prem Llama/vLLM handles all raw log analysis; cloud LLMs receive only structured, sanitized fields
- **OPA is the hard gate** — no LLM output executes directly; every remediation action passes through OPA Rego policies
- **Confidence threshold 0.85** for autonomous remediation; below that → human escalation
- **P1/P2 always require Slack/Teams human approval** before any mutating action
- **ReAct pattern per agent:** Observe → Retrieve (RAG) → Reason (LLM) → Policy Check → Act → Reflect → Emit
- **Rollback on every mutating action** — pre-state captured before execution; auto-rollback if post-validation fails

## Axway Integration Points

- **Admin REST API** (`https://axway-admin:444/api/v1.4`) — partner config, cert management, transfer management, service control
- **Filebeat log shipping** — tails Axway log files on host, ships to Kafka
- **Custom metrics exporter** — Axway JVM, connection pool, queue depth metrics to Prometheus

## Tech Stack (Planned)

- **Agent orchestration:** Python 3.12 + LangChain + LangGraph
- **Backend services:** FastAPI
- **Frontend:** React 19 + TypeScript
- **Infra:** Kubernetes, Helm, Terraform, ArgoCD
- **Data:** PostgreSQL 16, Redis 7, Elasticsearch 8, Qdrant, Neo4j
- **Streaming:** Apache Kafka, Apache Flink
- **Observability:** Prometheus, Grafana, Jaeger, OpenTelemetry

## Implementation Phases

- **Phase 1 (M1–3):** Log collection, Kafka pipeline, Triage Agent, Knowledge Base, ServiceNow integration
- **Phase 2 (M4–6):** RCA Agent, Remediation Agent (P3/P4 auto), Policy Engine, Predictive alerts
- **Phase 3 (M7–9):** Full autonomy for known patterns, cert renewal, key rotation, Compliance Agent
- **Phase 4 (M10–12):** Partner portal, capacity planning, change impact prediction
