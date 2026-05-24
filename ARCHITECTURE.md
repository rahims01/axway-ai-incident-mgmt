# Axway SecureTransport AI AIOps Platform — Enterprise Architecture Blueprint

**Version:** 1.0  
**Date:** 2026-05-21  
**Classification:** Internal Architecture Document  

---

## 1. Executive Summary

This document defines the architecture for an AI-native AIOps platform purpose-built for Axway SecureTransport Managed File Transfer (MFT) operations. The platform mirrors the capability philosophy of Nova AIOps — continuous telemetry ingestion, multi-agent AI reasoning, autonomous remediation, and conversational operations intelligence — adapted to the specific failure modes, protocols, and operational patterns of enterprise MFT.

Axway SecureTransport environments generate a dense, high-velocity stream of operational signals: SFTP handshake negotiations, AS2 MDN acknowledgements, TLS certificate validations, partner authentication events, transfer state transitions, and JVM health metrics. Today these signals are consumed reactively by support engineers who diagnose incidents manually from fragmented logs, often under SLA pressure. The result is high MTTR, repeated incidents, tribal knowledge dependency, and limited capacity to run proactive operations.

The proposed platform replaces this model with six cooperating AI agents — Triage, Root Cause Analysis, Autonomous Remediation, Knowledge, Predictive Analytics, and Compliance & Audit — orchestrated by a central coordinator, grounded in a RAG knowledge layer, and governed by a policy engine. The system ingests telemetry from Axway logs, SIEM, monitoring platforms, and ticketing systems; detects anomalies and incidents; reasons over root cause; executes approved remediations; and continuously improves from historical outcomes.

**Target outcomes:**
- MTTR reduction: 70–85% for known incident patterns
- Autonomous resolution rate: 40–60% of P3/P4 incidents in Phase 1, scaling to 70%+ in Phase 2
- Proactive detection: certificate expiry, key rotation, SLA breach prediction with 7–30 day lead time
- Engineer productivity: 3–5x increase in incidents handled per engineer per shift
- Audit readiness: continuous, automated compliance evidence generation

---

## 2. Functional Requirements

### 2.1 Incident Management
- FR-01: Ingest alerts from Axway logs, Splunk, ELK, Datadog, Prometheus, PagerDuty, email, and ticketing systems in real time
- FR-02: Correlate related alerts into a single incident within a configurable time window (default 5 min)
- FR-03: Classify incidents by protocol (SFTP, AS2, HTTPS/SSL, FTPS), failure type, and impacted partner
- FR-04: Assign severity (P1–P4) based on partner SLA tier, transfer volume, and failure pattern
- FR-05: Deduplicate incidents using fingerprinting (protocol + partner + failure code + time window)
- FR-06: Enrich incidents with partner profile, SLA commitment, historical failure rate, and contact info
- FR-07: Surface probable root cause with confidence score ≥ 0.75 for known patterns
- FR-08: Generate human-readable incident summary in ≤ 60 seconds of alert receipt

### 2.2 Root Cause Analysis
- FR-09: Parse and correlate Axway transfer logs, SSH/SFTP debug logs, TLS handshake logs, AS2 logs, JVM logs, and OS-level logs
- FR-10: Identify SFTP failures: key type mismatch, unsupported algorithm, host key changed, wrong key loaded, exhausted retries
- FR-11: Identify TLS/SSL failures: expired cert, wrong SAN, chain incomplete, cipher suite mismatch, protocol version mismatch
- FR-12: Identify AS2 failures: MDN timeout, MDN signature mismatch, disposition-notification-options mismatch, encryption failure
- FR-13: Identify network failures: DNS resolution, firewall block, TCP timeout, MTU issue
- FR-14: Identify Axway internal failures: mailbox routing error, adapter crash, queue overflow, disk full, JVM OOM
- FR-15: Correlate current incident to historical incidents with ≥ 80% structural similarity
- FR-16: Return structured RCA report: failure timeline, affected components, root cause category, contributing factors

### 2.3 Autonomous Remediation
- FR-17: Execute approved remediations against Axway Admin API, OS, and partner systems without human intervention for P3/P4
- FR-18: Support human-in-the-loop approval for P1/P2 remediations with Slack/Teams workflow
- FR-19: Implement rollback capability for all mutating actions within 15 minutes
- FR-20: Log every remediation action with actor (agent), timestamp, parameters, outcome, and rollback state
- FR-21: Support policy-based execution gates: maintenance windows, change freeze periods, partner-specific restrictions
- FR-22: Retry failed transfers with configurable back-off
- FR-23: Rotate expired SSL certificates using ACME, Vault, or CyberArk integration
- FR-24: Rotate SSH keys, update authorized_keys on Axway, notify partner
- FR-25: Restart stuck Axway services (SSH listener, AS2 adapter, HTTP server) with pre-check and post-check

### 2.4 Knowledge & Conversational AI
- FR-26: Ingest and index runbooks, SOPs, Axway documentation, historical tickets, architecture diagrams, partner onboarding docs
- FR-27: Support natural language queries from engineers via Slack, Teams, or web UI
- FR-28: Generate step-by-step troubleshooting guidance grounded in retrieved context
- FR-29: Maintain conversation history per session for multi-turn troubleshooting
- FR-30: Surface relevant runbook sections alongside RCA output automatically

### 2.5 Predictive Analytics
- FR-31: Predict SSL certificate expiry risk with 30/15/7/1 day alerts, accounting for renewal lead time
- FR-32: Detect transfer throughput degradation trends ≥ 3 days before SLA breach
- FR-33: Identify partners with rising failure rates indicating key/cert/config drift
- FR-34: Detect Axway resource exhaustion (disk, JVM heap, connection pool) before service impact
- FR-35: Score partner health daily and flag deteriorating partners for proactive engagement

### 2.6 Compliance & Audit
- FR-36: Maintain immutable audit log of all agent decisions and actions
- FR-37: Generate on-demand compliance reports: cipher suite inventory, cert expiry status, key algorithm inventory
- FR-38: Detect use of deprecated algorithms (MD5, SHA-1, RSA-1024, DES, RC4) and flag for remediation
- FR-39: Track changes to partner configurations with before/after diff and change attribution

---

## 3. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Availability | 99.9% platform uptime; agent services independently HA |
| Latency | Alert-to-triage ≤ 60s; RCA generation ≤ 120s for known patterns |
| Throughput | Ingest ≥ 50,000 log events/sec; process ≥ 500 incidents/hour |
| Scalability | Horizontal scale for all stateless components; Kafka partitioning for event streams |
| Security | Zero-trust network policy; all secrets in Vault/CyberArk; mTLS between services |
| Data Residency | Support on-prem and private cloud deployment; no Axway log data to public LLM APIs |
| Auditability | Every LLM call logged with prompt, response, model version, timestamp |
| Observability | Full distributed tracing (OpenTelemetry); metrics to Prometheus; logs to ELK |
| RTO/RPO | RTO ≤ 4h; RPO ≤ 1h for knowledge base; RPO ≤ 15min for incident state |
| Multi-tenancy | Logical tenant isolation for MSP deployments supporting multiple Axway environments |
| Compliance | SOC 2 Type II, ISO 27001, PCI-DSS compatible audit controls |

---

## 4. End-to-End Architecture

### 4.1 Architectural Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                                  │
│  Web UI (React)  │  Slack Bot  │  Teams Bot  │  REST API  │  CLI             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                         ORCHESTRATION LAYER                                  │
│           Agent Coordinator (LangGraph)  │  Policy Engine (OPA)             │
│           Workflow Engine (Temporal)     │  Human Approval Gateway           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                          AI AGENT LAYER                                      │
│  Triage Agent │ RCA Agent │ Remediation Agent │ Knowledge Agent              │
│  Predictive Agent │ Compliance Agent │ Synthetic Test Agent                  │
└───────┬───────────────┬──────────────┬──────────────┬──────────────┬────────┘
        │               │              │              │              │
┌───────▼───────┐ ┌─────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐ ┌────▼──────┐
│  LLM Gateway  │ │  RAG Layer │ │  Tools   │ │  Memory    │ │  ML Models│
│  (multi-model)│ │  (Vector + │ │  Layer   │ │  Store     │ │  (anomaly,│
│               │ │   Graph DB)│ │          │ │  (Redis)   │ │  predict) │
└───────────────┘ └────────────┘ └──────────┘ └────────────┘ └───────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                        EVENT PROCESSING LAYER                                │
│  Kafka (event bus)  │  Flink (stream processing)  │  Correlation Engine      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                         INTEGRATION LAYER                                    │
│  Axway ST Connector │ Splunk HEC │ ELK Beats │ Datadog Agent │ ServiceNow   │
│  PagerDuty │ Vault/CyberArk │ AD/LDAP │ SMTP │ Jira │ Prometheus             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                        DATA SOURCES (AXWAY + INFRA)                          │
│  Axway ST Logs │ Transfer DB │ SSH/SFTP Logs │ AS2 Logs │ TLS Logs           │
│  JVM Metrics │ OS Metrics │ Network Metrics │ Audit DB                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Core Design Principles

1. **Event-driven, not polling** — All telemetry flows via Kafka topics; agents are triggered by events, not cron
2. **Separation of reasoning from execution** — Agents reason; Tools execute; Policy Engine gates execution
3. **Grounded generation** — Every LLM output that drives action must cite retrieved context (RAG) or tool output; no free-form hallucinated commands
4. **Immutable audit** — Every decision, tool call, and LLM interaction written to append-only audit store
5. **Graceful degradation** — If LLM unavailable, fall back to rule-based triage; if Axway API unavailable, queue remediation actions
6. **Human-in-the-loop by default for P1/P2** — Autonomous execution requires explicit policy unlock per action type and severity

---

## 5. AI Agent Architecture

### 5.1 Agent Design Pattern

Each agent follows the ReAct (Reason + Act) pattern extended with RAG grounding:

```
┌─────────────────────────────────────────────────────────┐
│                      AGENT LIFECYCLE                     │
│                                                          │
│  INPUT EVENT                                             │
│      │                                                   │
│      ▼                                                   │
│  [OBSERVE] ──► Gather context from tools + memory       │
│      │                                                   │
│      ▼                                                   │
│  [RETRIEVE] ──► RAG lookup: similar incidents, runbooks │
│      │                                                   │
│      ▼                                                   │
│  [REASON] ──► LLM reasoning over context + retrieved    │
│      │         docs; generate hypothesis + next action   │
│      │                                                   │
│      ▼                                                   │
│  [POLICY CHECK] ──► OPA evaluates action against policy │
│      │                                                   │
│      ▼                                                   │
│  [ACT] ──► Execute tool call (Axway API, OS, etc.)      │
│      │                                                   │
│      ▼                                                   │
│  [REFLECT] ──► Evaluate outcome; update memory          │
│      │                                                   │
│      ▼                                                   │
│  [EMIT] ──► Publish result event to Kafka               │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Agent 1: Incident Triage Agent

**Purpose:** First responder. Converts raw alert signals into structured, enriched incidents.

**Inputs (Kafka topics):**
- `raw.alerts.axway` — parsed Axway log events
- `raw.alerts.monitoring` — Datadog/Prometheus alert webhooks
- `raw.alerts.siem` — Splunk/ELK alert forwards
- `raw.alerts.email` — parsed email alerts
- `raw.alerts.pagerduty` — PagerDuty event stream
- `raw.alerts.ticketing` — ServiceNow/Jira webhooks

**Processing steps:**
1. **Normalization** — Map all alert formats to canonical `AlertEvent` schema
2. **Deduplication** — Redis-based fingerprint cache (protocol + partner_id + error_code + 5min window)
3. **Correlation** — Sliding window grouping: alerts from same partner within 5 min → single incident
4. **Enrichment** — Partner profile lookup (Axway Admin API + CMDB), SLA tier, last 30-day failure rate
5. **Classification** — LLM classifies incident category from normalized alert + enrichment data
6. **Severity assignment** — Rule engine (P1: production partner, > 10 failures/min; P2: SLA at risk; P3/P4: isolated)
7. **Output** — Structured `Incident` object emitted to `incidents.structured`

**Key tools:**
- `axway_partner_lookup(partner_id)` — fetch partner profile from Axway Admin API
- `redis_fingerprint_check(fingerprint)` — deduplication
- `cmdb_lookup(hostname)` — infrastructure context
- `sla_lookup(partner_id)` — SLA commitment tier

**LLM prompt pattern:**
```
You are an incident triage specialist for an Axway SecureTransport MFT platform.

ALERT DATA:
{normalized_alert_json}

PARTNER CONTEXT:
{partner_profile}
{sla_tier}
{failure_history_30d}

SIMILAR PAST INCIDENTS:
{rag_retrieved_incidents}

Classify this incident:
1. Category: [SFTP_AUTH | SFTP_KEY | TLS_CERT | TLS_HANDSHAKE | AS2_MDN | AS2_ENCRYPT | 
              NETWORK | AXWAY_INTERNAL | QUEUE | DISK | JVM | API_AUTH | UNKNOWN]
2. Severity: [P1 | P2 | P3 | P4] with justification
3. Probable root cause (1-2 sentences)
4. Confidence: [0.0–1.0]
5. Impacted scope: [partner list, transfer count estimate]
6. Recommended next agent: [RCA | REMEDIATION | HUMAN_ESCALATION]

Respond in JSON only.
```

**Output schema:**
```json
{
  "incident_id": "INC-20260521-004421",
  "created_at": "2026-05-21T14:22:01Z",
  "category": "SFTP_KEY",
  "severity": "P2",
  "partner_id": "PARTNER-ABC",
  "partner_name": "Acme Corp",
  "sla_tier": "GOLD",
  "probable_cause": "SSH RSA key fingerprint mismatch — partner likely rotated their key without notifying ops",
  "confidence": 0.91,
  "alert_count": 14,
  "impacted_transfers": 47,
  "correlated_alert_ids": ["ALT-001", "ALT-002", "ALT-003"],
  "recommended_action": "RCA",
  "enrichment": { ... }
}
```

### 5.3 Agent 2: Root Cause Analysis Agent

**Purpose:** Deep-dive log analysis and causal reasoning to produce an actionable RCA report.

**Trigger:** `incidents.structured` topic, severity P1–P3

**Log sources ingested:**
- `/opt/axway/SecureTransport/var/log/tm.log` — transfer manager
- `/opt/axway/SecureTransport/var/log/admin.log` — admin events
- `/opt/axway/SecureTransport/var/log/sshd.log` — SSH/SFTP daemon
- `/opt/axway/SecureTransport/var/log/as2.log` — AS2 protocol
- `/opt/axway/SecureTransport/var/log/httpd.log` — HTTPS/API
- JVM GC logs, thread dumps
- OS: `/var/log/messages`, `netstat`, `ss`, `dmesg`
- Network: firewall deny logs, DNS query logs

**RCA reasoning chain:**

```
Step 1: TIME ANCHORING
  → Identify first failure timestamp from transfer log
  → Build ±10 min event window across all log sources

Step 2: PROTOCOL TRACE
  For SFTP: Extract full handshake sequence:
    - TCP connect → SSH version exchange → algorithm negotiation
    - Key exchange (KEX) → host key verification → user auth
    - Find exact step where failure occurred
  For TLS: Extract:
    - ClientHello → ServerHello → Certificate → CertificateVerify
    - Find exact alert code (e.g., certificate_expired=45, unknown_ca=48)
  For AS2: Extract:
    - HTTP POST → MDN generation → MDN receipt
    - Check signature, encryption, disposition-notification-options

Step 3: PATTERN MATCHING
  → Match extracted failure signature to known failure library (vector search)
  → Return top-3 matching historical incidents with resolution

Step 4: CAUSAL CHAIN CONSTRUCTION
  → LLM builds directed causal chain from evidence
  → Assigns confidence to each causal link

Step 5: CONTRIBUTING FACTOR ANALYSIS
  → Check: was there a recent change? (Axway audit log)
  → Check: did partner rotate keys? (SSH known_hosts comparison)
  → Check: is cert within 30 days of expiry?
  → Check: is there network instability? (packet loss metrics)
```

**Key tools available to RCA agent:**
```python
log_fetch(host, log_path, start_time, end_time, filter_regex)
axway_transfer_history(partner_id, start_time, end_time, status_filter)
axway_get_partner_config(partner_id)  # protocol, key, cert settings
ssh_keyscan(host, port)  # live scan of partner's current host key
openssl_cert_check(host, port)  # live cert inspection
axway_audit_log(entity_id, start_time, end_time)  # recent config changes
nmap_port_check(host, port)  # connectivity validation
dns_lookup(hostname)  # forward/reverse DNS
axway_transfer_state(transfer_id)  # current state of specific transfer
```

**Output schema:**
```json
{
  "incident_id": "INC-20260521-004421",
  "rca_id": "RCA-20260521-004421",
  "root_cause_category": "SFTP_KEY_MISMATCH",
  "root_cause_description": "Partner Acme Corp rotated their SFTP RSA host key on 2026-05-21T12:00Z. The Axway SecureTransport known_hosts entry still contains the old fingerprint SHA256:ABC123. All SFTP connections from 12:01Z onwards fail at the host key verification step with 'Host key verification failed'.",
  "confidence": 0.94,
  "evidence": [
    {"source": "sshd.log", "timestamp": "2026-05-21T12:01:33Z", "entry": "Warning: Permanently added ... (RSA) to known hosts", "significance": "Key changed"},
    {"source": "tm.log", "timestamp": "2026-05-21T12:01:34Z", "entry": "Transfer XFER-9921 failed: Host key verification failed", "significance": "Transfer failure"}
  ],
  "causal_chain": [
    "Partner rotated SSH host key",
    "Axway known_hosts not updated",
    "SSH handshake fails at host key verification",
    "Transfer fails with AUTH_FAILED",
    "Retry exhausted → transfer moves to FAILED state"
  ],
  "contributing_factors": ["No automated key rotation notification from partner"],
  "similar_incidents": ["INC-20250112-002201", "INC-20240830-009988"],
  "recommended_remediation": "UPDATE_KNOWN_HOSTS",
  "estimated_remediation_time": "5 minutes",
  "recommended_agent": "REMEDIATION"
}
```

### 5.4 Agent 3: Autonomous Remediation Agent

**Purpose:** Execute approved fixes against Axway SecureTransport and partner systems.

**Remediation catalog (indexed by RCA category):**

| RCA Category | Remediation Action | Approval Required |
|---|---|---|
| SFTP_KEY_MISMATCH | `update_known_hosts(partner_id, new_fingerprint)` | P1: Yes / P2-P4: No |
| TLS_CERT_EXPIRED | `renew_certificate(cert_id, via=vault)` | P1: Yes / P2: Yes / P3-P4: No |
| TLS_CHAIN_INCOMPLETE | `update_cert_chain(cert_id, chain_bundle)` | Always Yes |
| AS2_MDN_TIMEOUT | `retry_as2_transfer(transfer_id)` | No |
| QUEUE_STUCK | `clear_transfer_queue(queue_id, partner_id)` | No |
| DISK_FULL | `cleanup_expired_files(path, retention_days)` | No |
| JVM_OOM | `restart_axway_service(service=jvm, post_check=true)` | P1: Yes / else: No |
| SSH_LISTENER_DOWN | `restart_axway_service(service=ssh_listener)` | Yes |
| CIPHER_MISMATCH | `update_partner_cipher_suite(partner_id, ciphers)` | Yes |
| TRANSFER_FAILED | `retry_transfer(transfer_id, delay_seconds=30)` | No |
| CERT_EXPIRY_WARN | `schedule_cert_renewal(cert_id, target_date)` | No |

**Execution flow:**

```
1. Receive RCA output + recommended_remediation
2. Load remediation playbook from catalog
3. Policy Engine check (OPA):
   a. Is action allowed for this severity?
   b. Is partner in maintenance window?
   c. Is this action within change freeze period?
   d. Has this action been attempted in last 30 min? (prevent loops)
4. If approval required:
   a. Send Slack/Teams approval request with incident summary + proposed action
   b. Wait up to 15 min for response
   c. If no response → escalate to PagerDuty
5. Execute action via tool
6. Post-execution validation:
   a. Run synthetic SFTP/AS2/HTTPS test to partner
   b. Check Axway service health
   c. Verify transfer queue draining
7. If validation fails → rollback + escalate
8. Emit result to incidents.resolved or incidents.escalated
```

**Rollback capability:**

Every mutating tool captures pre-state before execution:
```python
class RemediationAction:
    def execute(self, params) -> ActionResult:
        self.pre_state = self.capture_state(params)  # snapshot
        result = self._do_execute(params)
        if not self._validate(result):
            self.rollback()
        return result
    
    def rollback(self):
        self._restore_state(self.pre_state)
        audit_log("ROLLBACK", self.action_id, self.pre_state)
```

### 5.5 Agent 4: Knowledge Agent

**Purpose:** Conversational assistant providing RAG-grounded troubleshooting guidance.

**Interfaces:**
- Slack slash command: `/axway-ops ask <question>`
- Teams bot: @AxwayOps `<question>`
- Web UI: chat panel in incident dashboard
- API: `POST /api/v1/knowledge/query`

**Knowledge sources indexed:**
- Axway SecureTransport Administration Guide (PDF → chunked)
- Axway SecureTransport Upgrade Guide
- Internal runbooks and SOPs (Confluence, SharePoint, Git)
- Historical ServiceNow/Jira tickets with resolution notes
- Partner onboarding documentation
- SSL certificate inventory (with metadata)
- SSH key inventory (with partner mapping)
- Architecture decision records
- RFC 4251 (SSH), RFC 4253 (SSH Transport), RFC 4960 (SCTP/AS2), RFC 5246 (TLS 1.2), RFC 8446 (TLS 1.3)

**Conversation memory pattern:**
```python
class KnowledgeAgentSession:
    session_id: str
    engineer_id: str
    incident_id: Optional[str]  # if launched from incident context
    turns: List[ConversationTurn]  # stored in Redis, TTL 4h
    working_memory: Dict  # facts established in this session
```

### 5.6 Agent 5: Predictive Analytics Agent

**Purpose:** Forward-looking detection of risk before it becomes an incident.

**Runs:** Scheduled (every 15 min for cert checks; every 1h for trend analysis) + triggered by anomaly detection

**Models:**
- **Certificate expiry predictor:** Rule-based with business calendar awareness. For each cert: `days_until_expiry = (expiry_date - today).days`. Alert thresholds: 30, 15, 7, 1 days. Factor in renewal lead time from Vault/CA.
- **Transfer throughput anomaly:** Facebook Prophet time series model trained on per-partner hourly transfer volumes. Detects deviations > 2σ from expected pattern.
- **Partner health scorer:** Logistic regression on: failure_rate_7d, avg_retry_count, cert_days_remaining, key_age_days, last_successful_transfer_age. Score 0–100; < 60 = at-risk.
- **SLA breach predictor:** Linear regression on transfer queue depth, average processing time trend, partner transfer volume forecast.

### 5.7 Agent 6: Compliance & Audit Agent

**Purpose:** Continuous compliance monitoring and audit evidence generation.

**Checks run continuously:**
- Cipher suite inventory: flag any partner using < TLS 1.2, RC4, DES, 3DES, MD5, SHA-1 MAC
- Key algorithm inventory: flag RSA < 2048-bit, DSA keys (deprecated), ECDSA curves < P-256
- Certificate algorithm inventory: flag SHA-1 signed certs
- Open SFTP sessions with no recent transfer: potential zombie connections
- AS2 partners with unsigned MDNs (compliance risk)
- Admin accounts with no MFA (if AD integration available)

---

## 6. Event Processing Architecture

### 6.1 Kafka Topic Design

```
Topic Namespace: axway-aiops.*

INBOUND (from data sources):
  axway-aiops.raw.logs.transfer        # Axway transfer log events
  axway-aiops.raw.logs.ssh             # SSH/SFTP daemon logs
  axway-aiops.raw.logs.as2             # AS2 protocol logs
  axway-aiops.raw.logs.tls             # TLS handshake logs
  axway-aiops.raw.logs.jvm             # JVM/GC logs
  axway-aiops.raw.logs.admin           # Axway admin audit logs
  axway-aiops.raw.alerts.monitoring    # Datadog/Prometheus/PagerDuty
  axway-aiops.raw.alerts.siem          # Splunk/ELK alert forwards
  axway-aiops.raw.alerts.email         # Parsed email alerts
  axway-aiops.raw.metrics.axway        # Axway performance metrics
  axway-aiops.raw.metrics.os           # OS/infra metrics

PROCESSING (internal):
  axway-aiops.events.normalized        # After normalization
  axway-aiops.events.correlated        # After correlation engine
  axway-aiops.incidents.structured     # After triage agent
  axway-aiops.incidents.rca            # After RCA agent
  axway-aiops.incidents.remediation    # Remediation decisions
  axway-aiops.incidents.resolved       # Closed incidents
  axway-aiops.incidents.escalated      # Human escalations

OUTBOUND (to external systems):
  axway-aiops.notifications.slack      # Slack messages
  axway-aiops.notifications.teams      # Teams messages
  axway-aiops.notifications.pagerduty  # PagerDuty triggers
  axway-aiops.sync.servicenow          # ServiceNow sync
  axway-aiops.sync.jira                # Jira sync
  axway-aiops.audit.immutable          # Append-only audit (compacted)
```

**Partition strategy:**
- Log topics: partitioned by `partner_id` hash → ensures ordering per partner
- Alert topics: partitioned by `alert_source` + `severity`
- Incident topics: partitioned by `incident_id` → ensures all events for one incident are co-located

**Retention:**
- Raw logs: 7 days (then archive to S3/object store)
- Incidents: 90 days (then archive)
- Audit: Infinite (compacted topic, archived to immutable store)

### 6.2 Stream Processing (Apache Flink)

**Flink jobs:**

1. **Log Parser Job** — Reads raw logs, applies regex/grok patterns per log type, emits `NormalizedEvent`
2. **Correlation Engine Job** — Sliding window (5 min) per `partner_id`; groups related events; emits `CorrelatedEventGroup`
3. **Anomaly Detection Job** — Real-time statistical anomaly detection on transfer metrics using Flink ML
4. **Deduplication Job** — Bloom filter-based deduplication on event fingerprints
5. **Metrics Aggregator Job** — Aggregates transfer counts, failure rates, latency percentiles per partner per minute

### 6.3 Log Parsing: Axway-Specific Patterns

```python
# Transfer Manager log pattern
TM_TRANSFER_PATTERN = re.compile(
    r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z)\s+'
    r'\[(?P<level>INFO|WARN|ERROR|DEBUG)\]\s+'
    r'Transfer\s+(?P<transfer_id>\w+)\s+'
    r'partner=(?P<partner_id>[\w-]+)\s+'
    r'status=(?P<status>STARTED|COMPLETED|FAILED|RETRYING)\s+'
    r'(?:error=(?P<error_code>\w+)\s+)?'
    r'(?:bytes=(?P<bytes>\d+)\s+)?'
    r'(?:duration=(?P<duration_ms>\d+)ms)?'
)

# SSH daemon log pattern (OpenSSH embedded in Axway)
SSH_AUTH_FAILURE_PATTERN = re.compile(
    r'(?P<timestamp>\w+ \d+ \d{2}:\d{2}:\d{2})\s+'
    r'sshd\[(?P<pid>\d+)\]:\s+'
    r'(?P<event>Failed|Accepted|Invalid|error:)\s+'
    r'(?P<auth_method>publickey|password|keyboard-interactive)\s+'
    r'for\s+(?P<username>\S+)\s+'
    r'from\s+(?P<src_ip>[\d.]+)\s+'
    r'port\s+(?P<src_port>\d+)'
)

# AS2 log pattern
AS2_MDN_PATTERN = re.compile(
    r'(?P<timestamp>[\d\-T:.Z]+)\s+AS2\s+'
    r'MessageID=(?P<message_id>[^\s]+)\s+'
    r'Partner=(?P<partner_id>[^\s]+)\s+'
    r'MDN-Status=(?P<mdn_status>processed|failed|pending)\s+'
    r'(?:MDN-Description=(?P<mdn_description>[^\n]+))?'
)
```

---

## 7. Data Flow Architecture

### 7.1 Primary Incident Data Flow

```
[Axway ST Host]
    │
    ├─► Filebeat (log tail) ──────────────────────────────────┐
    ├─► Axway Metrics Exporter (custom) ──────────────────────┤
    └─► Axway Admin API (polling, 30s) ───────────────────────┤
                                                              │
[Monitoring Systems]                                          │
    ├─► Datadog webhook ──────────────────────────────────────┤
    ├─► Prometheus Alertmanager webhook ──────────────────────┤
    └─► PagerDuty event API ──────────────────────────────────┤
                                                              ▼
                                              ┌─────────────────────────┐
                                              │   Kafka Ingest Topics   │
                                              └─────────────┬───────────┘
                                                            │
                                              ┌─────────────▼───────────┐
                                              │   Flink: Log Parser     │
                                              │   + Normalizer          │
                                              └─────────────┬───────────┘
                                                            │
                                              ┌─────────────▼───────────┐
                                              │   Flink: Correlation    │
                                              │   Engine (5min window)  │
                                              └─────────────┬───────────┘
                                                            │
                                              ┌─────────────▼───────────┐
                                              │   Triage Agent          │
                                              │   (LangGraph node)      │
                                              └─────────────┬───────────┘
                                                            │
                                    ┌───────────────────────┼────────────────────┐
                                    │                       │                    │
                          ┌─────────▼──────┐    ┌──────────▼──────┐   ┌────────▼──────┐
                          │  RCA Agent     │    │ Predictive Agent │   │ Compliance    │
                          └─────────┬──────┘    └──────────────────┘   │ Agent         │
                                    │                                   └───────────────┘
                          ┌─────────▼──────┐
                          │ Remediation    │
                          │ Agent          │
                          └─────────┬──────┘
                                    │
                    ┌───────────────┼────────────────┐
                    │               │                │
              ┌─────▼─────┐  ┌─────▼─────┐  ┌──────▼──────┐
              │ ServiceNow│  │  Slack/   │  │  PagerDuty  │
              │ Jira sync │  │  Teams    │  │  escalation │
              └───────────┘  └───────────┘  └─────────────┘
```

### 7.2 Data Schemas

**NormalizedEvent:**
```json
{
  "event_id": "EVT-uuid",
  "source_system": "axway_tm_log | sshd_log | datadog | splunk | ...",
  "source_host": "axway-prod-01",
  "timestamp": "2026-05-21T14:22:01.334Z",
  "event_type": "TRANSFER_FAILED | AUTH_FAILED | CERT_ERROR | AS2_MDN_FAIL | ...",
  "severity": "CRITICAL | HIGH | MEDIUM | LOW | INFO",
  "partner_id": "PARTNER-ABC",
  "protocol": "SFTP | AS2 | HTTPS | FTPS",
  "transfer_id": "XFER-9921",
  "error_code": "HOST_KEY_VERIFICATION_FAILED",
  "error_message": "Warning: Remote host identification has changed",
  "raw_log_line": "...",
  "metadata": {}
}
```

---

## 8. Security Architecture

### 8.1 Zero Trust Network Model

```
All inter-service communication:
  - mTLS enforced via Istio service mesh
  - Service identity via SPIFFE/SPIRE certificates
  - No lateral movement without explicit NetworkPolicy allow
  - All traffic encrypted in transit

Agent execution sandbox:
  - Each agent runs in isolated Kubernetes pod with minimal permissions
  - No direct Axway SSH access from agent pods — all through API Gateway layer
  - Tool execution layer is a hardened microservice with its own RBAC
```

### 8.2 Secret Management

```
All credentials managed by HashiCorp Vault (primary) or CyberArk (enterprise alt):
  - Axway Admin API credentials: Vault dynamic secrets (rotated every 1h)
  - SSH private keys for ST: Vault SSH secrets engine
  - LLM API keys: Vault KV with envelope encryption
  - Database credentials: Vault database secrets engine
  - Partner keys/certs: Vault PKI secrets engine

No credentials in:
  - Environment variables (except Vault token via Kubernetes SA)
  - ConfigMaps
  - Container images
  - Git repositories
```

### 8.3 LLM Security Controls

| Risk | Control |
|---|---|
| Prompt injection via log content | Log content sanitized before LLM injection; structured JSON fields only for untrusted data |
| Data exfiltration via LLM API | Private/self-hosted LLM for all log analysis; only classification/summary tasks use cloud LLM |
| Hallucinated remediation commands | Every command generated by LLM validated against allow-list before execution |
| Model poisoning via RAG | Document ingestion pipeline validates source, integrity-checks chunks; signed document manifests |
| Over-permissive autonomous actions | OPA policy engine as hard gate; no LLM output directly executes without policy check |

### 8.4 RBAC Model

```
Roles:
  aiops-viewer        → read-only access to incidents, dashboards
  aiops-operator      → approve remediation actions, query knowledge agent
  aiops-engineer      → manage runbooks, configure agents, view audit logs
  aiops-admin         → manage platform configuration, RBAC, integrations
  aiops-auditor       → read-only access to all audit logs and compliance reports
  aiops-agent         → service account for agents (scoped per agent type)

Attribute-Based Access Control (ABAC) overlays:
  - Partner data access: operators only see incidents for partners in their portfolio
  - Remediation scope: operators can approve only actions within their service scope
  - Audit data: auditors see all but cannot modify
```

### 8.5 Guardrails Framework

```python
class RemediationGuardrails:
    """Hard stops that cannot be overridden by any agent."""
    
    NEVER_EXECUTE = [
        "DROP TABLE", "DELETE FROM", "rm -rf /",    # destructive
        "iptables -F",                                # firewall flush
        "axway_delete_partner",                       # partner deletion
        "axway_delete_cert",                          # cert deletion (only revoke allowed)
    ]
    
    REQUIRE_DUAL_APPROVAL = [
        "restart_all_axway_services",
        "rotate_ca_certificate",
        "bulk_partner_config_update",
    ]
    
    MAX_BLAST_RADIUS = {
        "partner_config_update": 1,      # one partner at a time
        "service_restart": 1,            # one service at a time
        "cert_renewal": 5,               # batch up to 5
        "transfer_retry": 50,            # batch up to 50
    }
```

---

## 9. Deployment Architecture

### 9.1 Kubernetes Architecture

```
Namespace: axway-aiops

Deployments:
  aiops-api-gateway           (2 replicas, HPA 2-10)
  aiops-triage-agent          (3 replicas, HPA 3-15)
  aiops-rca-agent             (2 replicas, HPA 2-8)
  aiops-remediation-agent     (2 replicas — intentionally limited)
  aiops-knowledge-agent       (2 replicas, HPA 2-6)
  aiops-predictive-agent      (1 replica + GPU node for ML inference)
  aiops-compliance-agent      (1 replica)
  aiops-orchestrator          (2 replicas — LangGraph coordinator)
  aiops-event-processor       (Flink on K8s, 3 task managers)
  aiops-rag-service           (2 replicas, HPA 2-6)
  aiops-llm-gateway           (2 replicas — proxy to LLM backends)
  aiops-policy-engine         (3 replicas — OPA)
  aiops-audit-service         (2 replicas)
  aiops-notification-service  (2 replicas)
  aiops-web-ui                (2 replicas)

StatefulSets:
  kafka                       (3 brokers, 3 zookeepers OR KRaft mode)
  redis-cluster               (6 nodes — 3 primary, 3 replica)
  postgresql                  (1 primary, 2 read replicas — incident DB)
  elasticsearch               (3 nodes — log search + RAG metadata)
  qdrant / weaviate           (3 nodes — vector database)
  temporal-server             (3 nodes — workflow engine)

DaemonSets:
  filebeat                    (on Axway hosts — log shipping)
  axway-metrics-exporter      (on Axway hosts — custom metrics)
  node-exporter               (all nodes — OS metrics)
  falco                       (all nodes — runtime security)
```

### 9.2 Multi-Region HA

```
Region A (Primary):           Region B (Secondary / DR):
  Full stack active             Full stack standby
  Kafka topic replication       Kafka MirrorMaker 2
  PostgreSQL primary            PostgreSQL streaming replica
  Redis primary cluster         Redis replica cluster
  Vector DB primary             Vector DB replica
  Active agents                 Passive agents (warm standby)

Traffic routing:
  Global load balancer → Route 53 / Azure Traffic Manager
  Health check failover: RTO < 4h automated, < 1h with runbook
  
Data replication:
  Kafka: async replication (RPO 30s for events)
  PostgreSQL: sync replication (RPO 0 for incident state)
  Vector DB: async (RPO 1h — knowledge is rebuilt from source)
  Audit log: sync to both regions before ack (RPO 0)
```

### 9.3 Edge Agents (On-Prem Axway Support)

For organizations running Axway SecureTransport on-premises:

```
On-Prem:                                    Cloud:
  Axway ST servers                            AIOps Platform
       │                                            │
  [Edge Agent Pod]                                  │
    ├─ Filebeat (log collection)    ──────────────► Kafka (TLS)
    ├─ Metrics exporter             ──────────────► Prometheus remote write
    ├─ Axway API proxy              ◄────────────── Remediation agent calls
    └─ Synthetic test runner        ◄────────────── Predictive agent triggers
```

Edge agents are lightweight (< 2 CPU, < 4GB RAM) and only forward data outbound unless a remediation action is approved and dispatched.

---

## 10. Integration Architecture

### 10.1 Axway SecureTransport Integration

**Admin API integration (REST):**
```python
class AxwaySTClient:
    base_url: str  # https://axway-admin:444/api/v1.4
    auth: HTTPBasicAuth | OAuth2ClientCredentials
    
    # Core operations used by agents
    def get_transfer(self, transfer_id: str) -> Transfer
    def list_transfers(self, partner_id: str, status: str, since: datetime) -> List[Transfer]
    def retry_transfer(self, transfer_id: str) -> TransferResult
    def get_partner(self, partner_id: str) -> Partner
    def update_partner(self, partner_id: str, config: PartnerConfig) -> Partner
    def get_certificate(self, cert_id: str) -> Certificate
    def import_certificate(self, cert_pem: str, password: str) -> Certificate
    def get_ssh_known_hosts(self, partner_id: str) -> List[KnownHost]
    def update_ssh_known_host(self, partner_id: str, fingerprint: str, key_type: str)
    def list_services(self) -> List[ServiceStatus]
    def restart_service(self, service_name: str) -> ServiceResult
    def get_audit_entries(self, entity_id: str, since: datetime) -> List[AuditEntry]
```

**Direct log access:**  
Filebeat agents on Axway hosts tail log files and ship to Kafka using Logstash or direct Kafka output plugin. Log paths are configurable per Axway installation.

### 10.2 SIEM Integration

**Splunk:**  
- Inbound: Splunk Alerting webhook → `axway-aiops.raw.alerts.siem`
- Outbound: HEC (HTTP Event Collector) for writing enriched incidents back to Splunk index
- Saved searches for Axway-specific patterns can be managed by Compliance Agent

**ELK Stack:**  
- Filebeat → Logstash (parsing) → Elasticsearch index `axway-logs-*`
- Kibana dashboards for raw log exploration (complement to AI UI)
- Watcher alerts → Kafka topic via Logstash output

### 10.3 Ticketing Integration

**ServiceNow:**
```python
class ServiceNowSyncer:
    def create_incident(self, aiops_incident: Incident) -> str  # returns sys_id
    def update_incident(self, sys_id: str, updates: Dict)
    def add_work_note(self, sys_id: str, note: str)
    def resolve_incident(self, sys_id: str, resolution: str)
    def get_cmdb_ci(self, hostname: str) -> CMDBCI  # enrich with CMDB data
```

**Bi-directional sync:**  
- AIOps creates → ServiceNow INC  
- ServiceNow human resolution → sync back to AIOps as human-resolved outcome  
- Human resolution notes → ingested into RAG knowledge base for learning

### 10.4 Secret Stores

**HashiCorp Vault:**
```python
# PKI for cert renewal
vault_client.secrets.pki.generate_certificate(
    mount_point="axway-pki",
    name="partner-client-cert",
    common_name=f"{partner_id}.partners.company.com",
    ttl="8760h"  # 1 year
)

# SSH signing for key rotation
vault_client.secrets.ssh.sign_ssh_key(
    mount_point="axway-ssh",
    name="partner-sftp",
    public_key=new_public_key
)
```

---

## 11. Incident Lifecycle

```
STATE MACHINE:

  [NEW] 
    │ (alert received, correlation window)
    ▼
  [TRIAGING]
    │ (triage agent running)
    ├──► [DUPLICATE] → merged into parent
    ├──► [NOISE] → suppressed, logged
    ▼
  [TRIAGED]
    │ (structured incident created)
    ▼
  [RCA_IN_PROGRESS]
    │ (RCA agent running)
    ▼
  [RCA_COMPLETE]
    │
    ├──► [AWAITING_APPROVAL] (P1/P2 or policy-gated)
    │         │
    │         ├──► [APPROVED] → REMEDIATING
    │         └──► [REJECTED] → HUMAN_ASSIGNED
    │
    ├──► [REMEDIATING] (autonomous remediation)
    │         │
    │         ├──► [RESOLVED] (validation passed)
    │         └──► [REMEDIATION_FAILED] → HUMAN_ASSIGNED
    │
    └──► [HUMAN_ASSIGNED] (escalated to engineer)
              │
              ├──► [RESOLVED] (human resolved)
              └──► [ESCALATED] (escalated to vendor/partner)

RESOLVED:
  - Post-incident report generated
  - Resolution notes indexed to RAG
  - Metrics updated (MTTR, resolution method)
  - ServiceNow closed
  - PagerDuty resolved
```

---

## 12. Autonomous Remediation Flows

### 12.1 Flow: SSH Host Key Mismatch

```
TRIGGER: Transfer fails with "Host key verification failed" for partner ACME

1. Triage Agent
   ← log event: "Host key verification failed" × 14 occurrences in 5 min
   → incident: SFTP_KEY_MISMATCH, P2, partner=ACME, confidence=0.91

2. RCA Agent
   ← tool: log_fetch(axway-prod-01, sshd.log, T-10min, now)
   ← tool: axway_get_partner_config(ACME)  # current known_hosts entry
   ← tool: ssh_keyscan(partner-sftp.acme.com, 22)  # live scan
   → finds: known_hosts has SHA256:oldkey, live server has SHA256:newkey
   → root cause: partner rotated key, ST not updated
   → recommended remediation: UPDATE_KNOWN_HOSTS(ACME, SHA256:newkey, RSA)
   → confidence: 0.94

3. Policy Engine (OPA)
   ← query: is UPDATE_KNOWN_HOSTS allowed for P2 incident, partner ACME?
   ← facts: no maintenance window active, no change freeze, last attempt > 30 min ago
   → decision: ALLOW (P2 key update is in auto-approve policy)

4. Remediation Agent
   ← tool: axway_update_known_host(ACME, SHA256:newkey, RSA)
   → pre-state captured: {partner: ACME, fingerprint: SHA256:oldkey}
   → API call: PUT /api/v1.4/partners/ACME/ssh/knownHosts
   ← tool: synthetic_sftp_test(ACME)  # connect and list directory
   → result: SUCCESS, connection established, 0 errors

5. Audit + Notification
   → audit: {action: UPDATE_KNOWN_HOSTS, actor: remediation-agent, partner: ACME, 
              old_fingerprint: SHA256:oldkey, new_fingerprint: SHA256:newkey,
              outcome: SUCCESS, validated: true}
   → Slack: "✓ INC-004421 auto-resolved: Updated SSH known_hosts for Acme Corp.
              New fingerprint: SHA256:newkey. Validation: PASSED."
   → ServiceNow: INC closed, resolution note added
```

### 12.2 Flow: SSL Certificate Expiry

```
TRIGGER: Predictive agent flags cert expiring in 7 days

1. Predictive Agent
   → alert: cert CN=api.partner.com expires 2026-05-28, 7 days remaining
   → action: CREATE_INCIDENT(CERT_EXPIRY_WARN, P2)

2. RCA Agent (lightweight — known cause)
   → root cause: scheduled certificate expiry
   → recommended: RENEW_CERTIFICATE(cert_id=CERT-4421, via=vault)

3. Policy Engine
   → ALLOW: cert renewal is auto-approved for P2 < 7 days

4. Remediation Agent
   ← tool: vault_pki_issue_cert(common_name=api.partner.com, ttl=8760h)
   → new cert issued: CN=api.partner.com, valid until 2027-05-21
   ← tool: axway_import_certificate(new_cert_pem, partner_id=PARTNER-XYZ)
   ← tool: axway_assign_cert_to_partner(PARTNER-XYZ, new_cert_id)
   ← tool: synthetic_https_test(partner_url=https://api.partner.com/health)
   → result: SUCCESS, new cert verified, chain complete

5. Notification
   → Slack: "✓ Certificate for api.partner.com renewed. New expiry: 2027-05-21."
   → Compliance Agent: update cert inventory record
```

### 12.3 Flow: AS2 MDN Failure (Requires Approval)

```
TRIGGER: AS2 MDN not received for transfer XFER-8822 to partner GLOBALCO

1. Triage Agent → AS2_MDN_TIMEOUT, P1 (GLOBALCO is Platinum SLA tier)

2. RCA Agent
   ← tool: log_fetch(axway-prod-01, as2.log, T-30min, now)
   → finds: MDN expected within 300s, not received after 600s
   ← tool: axway_get_partner_config(GLOBALCO)  # AS2 config
   → finds: MDN URL = http://globalco-sftp.globalco.com:4080/as2 (HTTP, not HTTPS)
   ← tool: http_probe(http://globalco-sftp.globalco.com:4080/as2)
   → result: connection refused (partner MDN endpoint down)
   → root cause: partner AS2 MDN endpoint unreachable
   → recommended: NOTIFY_PARTNER + RETRY_AS2_TRANSFER_WITH_ASYNC_MDN

3. Policy Engine → REQUIRES_APPROVAL (P1, partner=GLOBALCO, action=RETRY)

4. Human Approval (Slack)
   → Message to #axway-ops-p1:
     "@oncall P1 INC-005511 — GLOBALCO AS2 MDN endpoint unreachable.
      Transfer XFER-8822 pending MDN for 10 min.
      Proposed action: Retry with async MDN fallback.
      [✅ Approve] [❌ Reject] [📋 View Details]"
   → Engineer approves within 3 min

5. Remediation Agent
   ← tool: axway_retry_as2_transfer(XFER-8822, mdn_mode=ASYNC)
   → transfer retried; async MDN scheduled
   → escalation created in ServiceNow for GLOBALCO partner contact
```

---

## 13. RAG + Knowledge Architecture

### 13.1 Vector Database Architecture

**Selected: Qdrant** (self-hosted, supports payload filtering for tenant isolation)  
**Alternative: Weaviate** (richer GraphQL query interface)

```
Collections:
  runbooks          → operational procedures
  incidents         → historical incident + resolution pairs
  axway_docs        → Axway product documentation
  partner_docs      → partner onboarding/config docs
  rfc_docs          → relevant RFC standards
  cert_inventory    → certificate metadata (not PEM — metadata only)
  key_inventory     → SSH key metadata

Per-document metadata (payload):
  source_type, source_id, partner_id (if applicable),
  protocol (SFTP|AS2|HTTPS|FTPS|ALL), 
  incident_category, created_at, last_updated,
  chunk_index, total_chunks, doc_version
```

**Embedding model:** `text-embedding-3-large` (OpenAI, 3072-dim) for cloud mode;  
`nomic-embed-text` or `bge-large-en-v1.5` for on-prem/air-gapped deployment

### 13.2 Document Ingestion Pipeline

```
SOURCE DOCUMENT
    │
    ▼
[Format Detection]  (PDF, DOCX, HTML, Markdown, plain text)
    │
    ▼
[Text Extraction]   (Apache Tika for PDFs/DOCX; markdown-it for MD)
    │
    ▼
[Cleaning]          (remove headers/footers, normalize whitespace,
                     extract structured sections)
    │
    ▼
[Chunking Strategy]
    ├─ Runbooks: chunk by step (each numbered step = 1 chunk + context header)
    ├─ Incident tickets: chunk whole ticket (≤ 1500 tokens) + resolution note
    ├─ Axway docs: recursive character chunking (512 tokens, 50 token overlap)
    └─ RFC docs: chunk by section (section number = metadata)
    │
    ▼
[Metadata Enrichment]  (classify protocol, incident_category via LLM)
    │
    ▼
[Embedding Generation] (batch, with retry + rate limiting)
    │
    ▼
[Qdrant Upsert]        (with deduplication by source_id hash)
    │
    ▼
[Metadata Store]       (PostgreSQL: doc_id, version, chunk_count, 
                         ingestion_status, last_updated)
```

### 13.3 Retrieval Strategy

**Hybrid retrieval (sparse + dense):**
```python
def retrieve(query: str, filters: Dict, top_k: int = 10) -> List[Chunk]:
    # 1. Dense retrieval (semantic similarity)
    dense_results = qdrant.search(
        collection=determine_collection(filters),
        query_vector=embed(query),
        query_filter=build_filter(filters),  # protocol, incident_category
        limit=top_k * 2
    )
    
    # 2. Sparse retrieval (BM25 keyword match via Elasticsearch)
    sparse_results = es.search(
        index="aiops-knowledge",
        body={"query": {"match": {"content": query}}},
        size=top_k * 2
    )
    
    # 3. Reciprocal Rank Fusion
    fused = rrf_merge(dense_results, sparse_results, k=60)
    
    # 4. Reranking (cross-encoder)
    reranked = cross_encoder.rerank(query, fused[:20])
    
    return reranked[:top_k]
```

### 13.4 Knowledge Graph (Supplementary)

Neo4j graph for relationship-aware retrieval:

```
Nodes: Partner, Certificate, SSHKey, Protocol, AxwayService, Incident, Runbook
Edges: USES_CERT, HAS_KEY, CONNECTS_VIA, CAUSED_BY, RESOLVED_BY, DOCUMENTED_IN

Example query:
  MATCH (p:Partner {id: "ACME"})-[:USES_CERT]->(c:Certificate)
  WHERE c.expiry_date < date() + duration({days: 30})
  RETURN p.name, c.subject, c.expiry_date, c.issuer
  → "Acme Corp uses cert CN=sftp.acme.com expiring 2026-06-01"
```

---

## 14. LLM Strategy

### 14.1 Multi-Model Architecture

| Task | Model | Rationale |
|---|---|---|
| Incident triage / classification | Claude Haiku 4.5 | Low latency (< 2s), cost-efficient, sufficient for classification |
| RCA reasoning over logs | Claude Sonnet 4.6 | Strong reasoning, large context window for log analysis |
| Remediation planning (P1/P2) | Claude Opus 4.7 | Highest accuracy for high-stakes decisions |
| Conversational Q&A (Knowledge Agent) | Claude Sonnet 4.6 | Good balance of quality and speed for interactive use |
| Document summarization (ingestion) | Claude Haiku 4.5 | Bulk processing — cost matters |
| Predictive narrative generation | Claude Haiku 4.5 | Templated output, LLM used for narrative only |
| Compliance report generation | Claude Sonnet 4.6 | Structured output, moderate complexity |
| Embedding generation | text-embedding-3-large (cloud) / bge-large (on-prem) | |

**Private/On-Prem LLM options (for log analysis — sensitive data):**
- **Llama 3.3 70B** via Ollama or vLLM — strong reasoning, fits 2× A100 80GB
- **Mistral Large** — strong multilingual, good for structured output
- **Qwen2.5 72B** — strong at code and structured reasoning

**Routing logic:**
```python
def select_model(task: Task, data_sensitivity: str) -> LLMClient:
    if data_sensitivity == "HIGH":  # contains raw log data
        return private_llm_client  # on-prem Llama/Mistral
    
    match task.type:
        case "TRIAGE": return claude_haiku
        case "RCA": return claude_sonnet
        case "REMEDIATION_PLAN" if task.severity in ("P1", "P2"): return claude_opus
        case "REMEDIATION_PLAN": return claude_sonnet
        case "KNOWLEDGE_QA": return claude_sonnet
        case _: return claude_haiku
```

### 14.2 Context Window Management

Axway logs can be verbose. Strategy for fitting within context windows:

1. **Log sampling:** For high-volume failures, take first occurrence + last 5 occurrences + 3 samples from middle
2. **Log compression:** Remove repeated identical lines, summarize with count (`[×47] same error`)
3. **Structured extraction:** Run regex/parser first; pass structured JSON fields to LLM, not raw text
4. **Progressive summarization:** For very long incidents, summarize earlier log windows before passing to next reasoning step

### 14.3 Prompt Engineering Patterns

**System prompt (RCA Agent):**
```
You are an expert Axway SecureTransport MFT operations engineer with deep knowledge of:
- SFTP protocol (RFC 4251, 4253, 4254): key exchange algorithms (curve25519, ecdh-sha2-nistp256, 
  diffie-hellman-group14-sha256), host key types (RSA, ECDSA, Ed25519), authentication methods
- TLS/SSL: handshake phases, alert codes, certificate chain validation, cipher suite negotiation,
  SNI, OCSP stapling
- AS2 protocol: MDN types (sync/async), S/MIME signing, encryption, disposition-notification-options
- Axway SecureTransport internals: Transfer Manager, SSHD adapter, AS2 adapter, HTTP server,
  mailbox routing, transfer states (WAITING, PROCESSING, COMPLETED, FAILED, RETRYING)
- Common failure patterns and their exact log signatures in Axway ST 5.x

When analyzing incidents:
1. Always cite the specific log line(s) that evidence your conclusion
2. Provide confidence scores (0.0–1.0) for each hypothesis
3. Never suggest remediations that are irreversible without explicit flagging
4. If the root cause is ambiguous, present top-2 hypotheses ranked by confidence
5. Structure all output as valid JSON matching the RCA schema
```

### 14.4 Hallucination Prevention

1. **Tool-grounded reasoning:** LLM must request tool calls to get facts; cannot assert facts from training alone for specific partner configs, cert fingerprints, or transfer IDs
2. **Citation requirement:** Every RCA conclusion must cite a specific log line from tool output
3. **Schema validation:** All LLM outputs validated against Pydantic schema before use; invalid output triggers retry
4. **Confidence gating:** If confidence < 0.70, incident escalated to human rather than autonomous remediation
5. **Cross-check:** For P1/P2 incidents, RCA output is independently verified by a second LLM call with different temperature

---

## 15. Multi-Agent Coordination

### 15.1 Orchestration: LangGraph

LangGraph provides stateful, graph-based agent orchestration with:
- Persistent state across agent hops (incident state machine)
- Conditional routing (based on severity, confidence, policy outcome)
- Human-in-the-loop nodes (pause for approval)
- Checkpointing (resume from last checkpoint if agent fails)

**Main graph:**
```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(IncidentState)

workflow.add_node("triage", triage_agent)
workflow.add_node("rca", rca_agent)
workflow.add_node("remediation", remediation_agent)
workflow.add_node("human_review", human_approval_node)
workflow.add_node("escalate", escalation_node)
workflow.add_node("resolve", resolution_node)

workflow.add_conditional_edges(
    "triage",
    route_after_triage,
    {
        "rca": "rca",
        "noise": END,
        "duplicate": END,
    }
)

workflow.add_conditional_edges(
    "rca",
    route_after_rca,
    {
        "auto_remediate": "remediation",
        "human_review": "human_review",
        "escalate": "escalate",
    }
)

workflow.add_conditional_edges(
    "remediation",
    route_after_remediation,
    {
        "resolved": "resolve",
        "failed": "escalate",
        "retry": "rca",
    }
)

workflow.add_edge("human_review", "remediation")
workflow.add_edge("resolve", END)
workflow.add_edge("escalate", END)
```

### 15.2 Comparison: LangGraph vs CrewAI vs AutoGen

| Dimension | LangGraph | CrewAI | AutoGen |
|---|---|---|---|
| State management | Explicit graph state, persistent | Role-based, less structured | Conversation-based |
| Human-in-loop | First-class (interrupt nodes) | Limited | Via custom reply functions |
| Determinism | High (graph-defined routing) | Medium (agent decides routing) | Low (conversation-driven) |
| Debugging | Excellent (LangSmith tracing) | Moderate | Moderate |
| Production maturity | High | Medium | Medium |
| Incident workflow fit | **Best** — strict state machine needed | OK | Poor for strict workflows |

**Decision: LangGraph** for incident orchestration.  
**Temporal.io** for long-running remediation workflows (cert renewal, key rotation) that may span hours.

### 15.3 Agent Communication Protocol

Agents communicate via Kafka events (primary) and shared PostgreSQL state:

```python
# Every agent emits this envelope
class AgentOutput(BaseModel):
    incident_id: str
    agent_type: AgentType
    agent_version: str
    timestamp: datetime
    state_transition: str  # e.g., "TRIAGING → TRIAGED"
    payload: Dict  # agent-specific output
    confidence: float
    next_recommended_action: Optional[str]
    human_review_required: bool
    audit_id: str  # reference to audit log entry
```

---

## 16. Monitoring & Observability

### 16.1 Platform Observability Stack

**Metrics:** Prometheus + Grafana  
**Traces:** OpenTelemetry → Jaeger / Tempo  
**Logs:** Fluent Bit → Elasticsearch  
**Dashboards:** Grafana  

### 16.2 Key Platform Metrics

```
aiops_incidents_total{severity, category, resolution_method}
aiops_incident_triage_duration_seconds{severity}
aiops_rca_duration_seconds{category}
aiops_remediation_duration_seconds{action_type, outcome}
aiops_remediation_success_rate{action_type}
aiops_llm_request_duration_seconds{model, agent_type}
aiops_llm_token_usage_total{model, agent_type}
aiops_rag_retrieval_latency_seconds{collection}
aiops_kafka_consumer_lag{topic, consumer_group}
aiops_approval_pending_count{severity}
aiops_agent_error_rate{agent_type}
aiops_axway_cert_days_remaining{cert_id, partner_id}
aiops_partner_health_score{partner_id}
```

### 16.3 Axway-Specific Operational Dashboards

1. **Transfer Health Dashboard:** Real-time transfer success rate per partner per protocol; failure rate trend; queue depth
2. **Certificate Inventory Dashboard:** All certs with days-to-expiry; color-coded risk (red < 7d, amber < 30d)
3. **SSH Key Inventory Dashboard:** All partner keys, age, algorithm, last validation
4. **Incident Timeline Dashboard:** Active incidents, MTTR by severity, resolution method breakdown
5. **Agent Performance Dashboard:** Per-agent latency, throughput, error rate, LLM cost

---

## 17. MLOps / AIOps Lifecycle

### 17.1 Continuous Learning Loop

```
INCIDENT OCCURS
    │
    ▼
AGENT RESOLVES (or human resolves)
    │
    ▼
OUTCOME CAPTURED (resolution method, time, accuracy of RCA)
    │
    ▼
FEEDBACK INGESTED INTO RAG (resolution notes → new knowledge chunks)
    │
    ▼
MODEL PERFORMANCE TRACKED:
  - RCA accuracy (did suggested root cause match actual?)
  - Remediation success rate per action type
  - False positive rate for anomaly detection
    │
    ▼
PERIODIC RETRAINING TRIGGERS:
  - Anomaly detection model: weekly retrain if drift detected
  - Partner health model: monthly retrain
  - RAG reindex: continuous (new docs trigger immediate ingestion)
    │
    ▼
A/B TESTING:
  - New LLM prompt versions tested on 10% of traffic
  - Metric: RCA accuracy, triage classification F1
```

### 17.2 RCA Accuracy Measurement

```python
# After incident closes, record ground truth
class IncidentOutcome(BaseModel):
    incident_id: str
    agent_rca_category: str        # what RCA agent said
    agent_confidence: float
    human_confirmed_rca: str       # what engineer confirmed
    rca_correct: bool              # agent_rca == human_confirmed
    remediation_action_taken: str
    remediation_outcome: str       # SUCCESS | FAILED | PARTIAL
    resolution_time_seconds: int
    resolution_method: str         # AUTONOMOUS | HUMAN_ASSISTED | HUMAN_ONLY
```

---

## 18. Implementation Roadmap

### Phase 1 — Foundation (Months 1–3)

**Goal:** Basic ingestion, triage, knowledge base, alerting

| Deliverable | Description |
|---|---|
| Axway Log Collector | Filebeat agents on all Axway hosts, shipping to Kafka |
| Log Parser (Flink) | Parse TM, SSH, AS2, TLS logs into NormalizedEvents |
| Triage Agent v1 | Rule-based triage + LLM classification; creates structured incidents |
| Knowledge Base v1 | Ingest runbooks, Axway docs, top-50 historical tickets |
| Knowledge Agent v1 | Conversational Q&A over knowledge base via Slack |
| ServiceNow Integration | Bi-directional incident sync |
| Basic Dashboards | Grafana: transfer health, cert expiry, active incidents |
| Alert Routing | PagerDuty and Slack notifications for P1/P2 |

**KPIs:** 100% of incidents create structured record; knowledge agent answers 70% of queries without escalation

### Phase 2 — Intelligence (Months 4–6)

**Goal:** Automated RCA, autonomous remediation for P3/P4, predictive alerts

| Deliverable | Description |
|---|---|
| RCA Agent v1 | Full log analysis + pattern matching for top 15 incident categories |
| Remediation Agent v1 | Auto-remediation for: key mismatch, transfer retry, queue clear, disk cleanup |
| Policy Engine (OPA) | Gating rules for all remediation actions |
| Human Approval Workflow | Slack-based approval for P1/P2 remediations |
| Predictive Agent v1 | Cert expiry prediction; partner health scoring |
| RAG Enhancement | Hybrid retrieval, reranking, cross-encoder |
| Temporal Workflows | Cert renewal, key rotation workflows |

**KPIs:** 40% autonomous resolution rate for P3/P4; MTTR reduction 50%

### Phase 3 — Autonomy (Months 7–9)

**Goal:** Full autonomous operation for known patterns; predictive prevention

| Deliverable | Description |
|---|---|
| RCA Agent v2 | Handles 25+ incident categories; confidence scoring mature |
| Remediation Agent v2 | Cert renewal, key rotation, AS2 config updates, service restart |
| Predictive Agent v2 | SLA breach prediction, transfer throughput anomaly detection |
| Knowledge Graph | Neo4j integration for relationship-aware retrieval |
| Compliance Agent | Cipher inventory, key algorithm audit, continuous monitoring |
| Multi-region HA | DR deployment, automated failover tested |
| Fine-tuning | Domain-specific fine-tune on Axway incident data |

**KPIs:** 60% autonomous resolution; MTTR reduction 75%; zero missed cert expirations

### Phase 4 — Intelligence Amplification (Months 10–12)

**Goal:** Predictive prevention, partner self-service, advanced analytics

| Deliverable | Description |
|---|---|
| Partner Portal | Web UI for partners to see their transfer health, raise issues |
| Capacity Planning Agent | Disk, JVM, connection pool capacity forecasting |
| Change Impact Prediction | Pre-change risk scoring for Axway config changes |
| SLA Reporting Automation | Auto-generate monthly SLA reports per partner |
| Advanced Anomaly Detection | Multivariate anomaly detection across all metrics |
| Vendor Escalation Agent | Auto-draft Axway support tickets with diagnostic bundle |

**KPIs:** 70%+ autonomous resolution; partner onboarding time reduced 60%

---

## 19. Recommended Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Agent Orchestration | LangGraph 0.2+ | Production-grade, stateful, human-in-loop |
| Long-running Workflows | Temporal.io | Durable execution for cert renewal, multi-step remediation |
| LLM (cloud tasks) | Claude Sonnet/Opus via Anthropic API | Best reasoning for RCA/remediation |
| LLM (sensitive/on-prem) | Llama 3.3 70B via vLLM | Air-gap compatible, strong reasoning |
| Embedding | text-embedding-3-large (cloud) / bge-large-en-v1.5 (on-prem) | |
| Vector Database | Qdrant | Self-hosted, fast, payload filtering, Rust performance |
| Graph Database | Neo4j | Knowledge graph, relationship traversal |
| Message Streaming | Apache Kafka (Confluent Platform or MSK) | Enterprise-grade, proven for log ingestion |
| Stream Processing | Apache Flink | Stateful stream processing, Kafka native |
| Workflow Automation | Temporal.io | Durable, retryable workflows |
| Policy Engine | Open Policy Agent (OPA) | Standard, auditable, Rego policies |
| Secret Management | HashiCorp Vault | Dynamic secrets, PKI, SSH signing |
| Service Mesh | Istio | mTLS, traffic management, observability |
| Container Platform | Kubernetes (EKS / AKS / on-prem K8s) | |
| Observability | Prometheus + Grafana + Jaeger + OTel | Standard cloud-native stack |
| Log Aggregation | ELK Stack (Elasticsearch 8+) | |
| API Gateway | Kong or AWS API Gateway | Rate limiting, auth, routing |
| Backend Services | Python 3.12 (FastAPI) | AI ecosystem compatibility |
| Frontend | React 19 + TypeScript | Modern, component-based |
| Agent Framework | LangChain + LangGraph | Tool integration, RAG pipelines |
| Database (incidents) | PostgreSQL 16 | ACID, JSON support, partitioned tables |
| Cache / Session | Redis 7 Cluster | High-throughput, Lua scripting for dedup |
| Document Ingestion | Apache Tika + LangChain loaders | Universal format support |
| Reranking | cross-encoder/ms-marco-MiniLM-L-6-v2 | Fast, accurate reranking |
| MLOps | MLflow | Experiment tracking, model registry |
| CI/CD | GitLab CI or GitHub Actions + ArgoCD | GitOps deployment |
| IaC | Terraform + Helm | Reproducible infrastructure |

---

## 20. Example Incident Scenarios

### Scenario A: ECDSA Key Algorithm Incompatibility

**Situation:** Partner upgraded their SFTP server and now only advertises `ecdsa-sha2-nistp521` host key. Axway ST is configured with `HostKeyAlgorithms rsa-sha2-256,rsa-sha2-512` and doesn't include ECDSA.

**Agent trace:**
1. Triage: 23 `No matching host key type found` errors in 4 min → INC P2, SFTP_KEY, ACME
2. RCA: Extracts `debug2: peer server ECDSA host key SHA256:xyz` and `Unable to negotiate... no matching host key type` from sshd.log; fetches Axway partner config showing RSA-only HostKeyAlgorithms; confirms via ssh_keyscan that server only presents ECDSA
3. Remediation: Updates partner SFTP config in Axway to add `ecdsa-sha2-nistp521` to allowed host key algorithms; runs synthetic SFTP test → success
4. Resolution: 6 minutes total, zero human involvement

### Scenario B: AS2 Certificate Chain Incomplete (P1)

**Situation:** Partner's AS2 signing certificate was renewed but only the leaf cert was loaded; intermediate CA missing. Axway rejects all inbound AS2 messages.

**Agent trace:**
1. Triage: PagerDuty alert + 156 AS2 failures in 2 min → P1, GLOBALCO (Platinum)
2. RCA: Parses AS2 log showing `PKIX path building failed: unable to find valid certification path to requested target`; runs `openssl_cert_check(partner_as2_endpoint)` which confirms chain: leaf → gap → root (missing intermediate)
3. Policy engine: P1 AS2 config update requires approval
4. Human approval: Slack to #axway-ops-p1 with exact error + proposed fix (import intermediate CA bundle); approved in 2 min
5. Remediation: Downloads intermediate CA from partner's CA disclosure (AIA extension); imports to Axway trust store; restarts AS2 adapter; validates with synthetic AS2 test
6. Resolution: 9 minutes with 2-min human approval

### Scenario C: JVM Heap Exhaustion Causing Transfer Slowdown

**Situation:** Axway Transfer Manager JVM hitting 90% heap, causing GC pauses, transfer throughput dropping 70%.

**Agent trace:**
1. Predictive Agent detects: transfer throughput dropping below 2σ threshold for 45 min; JVM heap metric at 89%
2. Triage: Creates P2 incident AXWAY_INTERNAL/JVM
3. RCA: Fetches JVM GC log — sees full GC every 30s, pause times 8–12s; thread dump shows many threads in `WAITING` on transfer queue; correlates with increased inbound transfer volume from 3 partners in last 2h
4. Remediation: 
   - Immediate: Increase JVM heap `-Xmx` from 4G to 8G + restart TM (approved — P2)
   - Longer term: Schedule maintenance window for JVM tuning
5. Post-action: Throughput recovers to baseline in 4 min post-restart

---

## 21. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| LLM hallucinated remediation commands | Medium | Critical | Allow-list validation, schema enforcement, confidence gating |
| Remediation loop (agent retries same broken action) | Low | High | Per-action cooldown (30 min), max retry count (3), circuit breaker |
| Axway API credential exposure | Low | Critical | Vault dynamic secrets, short-lived tokens, network policy |
| False positive autonomous remediation | Medium | High | Confidence threshold ≥ 0.85 for auto-remediation; P1/P2 require approval |
| Knowledge base poisoning | Low | Medium | Signed document manifests, source validation, ingestion audit |
| Agent cascade failure | Low | High | Independent agent deployments, dead letter queues, fallback to rule-based |
| LLM API unavailability | Medium | Medium | Circuit breaker, fallback to rule-based triage, queue incidents for later AI analysis |
| Axway API unavailability | Medium | High | Local cache of partner configs, read-only mode, queue remediations |
| Prompt injection via log content | Medium | High | Structured data injection only, log content in JSON fields not prompt interpolation |
| Partner data leakage via LLM | Low | Critical | On-prem LLM for all log analysis; data classification before routing |

---

## 22. Cost Optimization

### LLM Cost Management
- Route 80% of triage decisions to Haiku (5× cheaper than Sonnet)
- Use streaming responses; cancel if confidence threshold met early
- Cache identical LLM prompts in Redis (TTL 5 min) — repeated incidents with same fingerprint
- Batch document summarization tasks for off-peak hours
- **Estimated monthly LLM cost at 500 incidents/day:** ~$800–1,200 (Haiku-heavy routing)

### Infrastructure Cost Management
- Predictive Agent ML models run on spot/preemptible GPU instances (inference, not training)
- Flink auto-scales task managers based on Kafka lag
- Vector DB: right-size per collection; prune embeddings older than 2 years
- Log retention: raw logs compress to S3 Glacier after 7 days (90% cost reduction)

### Cost vs. Value
- At 500 incidents/month, each requiring 45 min engineer time → 375 engineer-hours/month
- At 60% autonomous resolution → 225 hours saved → ~$45,000/month engineer cost avoided
- Platform cost (infra + LLM): ~$8,000–15,000/month
- **ROI: 3–5× in Year 1**

---

## 23. Scalability Considerations

### Kafka Scaling
- Start: 3 brokers, 12 partitions per high-volume topic
- Scale trigger: consumer lag > 10,000 events → add partitions (Kafka 3.x supports partition scaling)
- At 50,000 events/sec: ~10 Kafka brokers with 3× replication = ~150,000 events/sec capacity

### Agent Scaling
- Triage and RCA agents are stateless per-incident → HPA on CPU + custom Kafka lag metric
- Remediation agent intentionally limited (max 2 concurrent remediations per partner, 10 globally)
- Knowledge agent scales on RPS; LLM is the bottleneck — LLM gateway pools connections

### Vector DB Scaling
- Qdrant: horizontal sharding by collection at > 10M vectors
- At 100K incidents/year × 10 chunks = 1M incident vectors — single shard sufficient for 3 years

### Database Scaling
- PostgreSQL: partition incident table by month; archive to cold storage after 12 months
- Read replicas for analytics queries; primary for writes only

---

## 24. Governance and Compliance

### Change Management
- All remediation actions recorded in ServiceNow as automated change records
- Change freeze calendar enforced by OPA policy engine
- Emergency changes (P1) bypass freeze with mandatory post-hoc review

### Data Governance
- PII in partner data masked in LLM prompts (partner contact names → `PARTNER_CONTACT_1`)
- Log data classified at ingestion (PUBLIC | INTERNAL | CONFIDENTIAL)
- CONFIDENTIAL logs → on-prem LLM only; never to cloud LLM APIs
- Data retention policy enforced by automated Kafka compaction + S3 lifecycle rules

### Model Governance
- Every LLM call logged: model ID, version, input token count, output token count, timestamp
- Prompt templates version-controlled in Git; changes require peer review
- Monthly model performance review: RCA accuracy, false positive rate, resolution accuracy
- Model retirement policy: if accuracy drops > 10% from baseline → human review gate activated

### Audit Trail
- Immutable audit log (Apache Kafka compacted topic + S3 WORM bucket)
- Every agent action: who (agent ID + version), what (action + parameters), when, outcome
- Human approvals: approver identity, timestamp, decision, justification
- Export to SIEM (Splunk) for SOC 2 evidence collection

---

## 25. Sample Agent Workflows

### Sample OPA Policy (Rego)

```rego
package axway.aiops.remediation

import future.keywords.if

# Default deny
default allow = false

# Allow transfer retry for any severity without approval
allow if {
    input.action_type == "RETRY_TRANSFER"
    input.severity in {"P3", "P4"}
}

# Allow known_hosts update for P2/P3/P4 without approval
allow if {
    input.action_type == "UPDATE_KNOWN_HOSTS"
    input.severity in {"P2", "P3", "P4"}
    not in_change_freeze
    not partner_in_maintenance(input.partner_id)
}

# Require approval for P1 known_hosts update
allow if {
    input.action_type == "UPDATE_KNOWN_HOSTS"
    input.severity == "P1"
    input.human_approved == true
}

# Cert renewal: auto for P2-P4 if < 30 days remaining
allow if {
    input.action_type == "RENEW_CERTIFICATE"
    input.severity in {"P2", "P3", "P4"}
    input.cert_days_remaining <= 30
    not in_change_freeze
}

# Never allow destructive actions without dual approval
deny if {
    input.action_type in {"DELETE_PARTNER", "REVOKE_CA_CERT", "DROP_TRANSFER_LOG"}
}

in_change_freeze if {
    data.change_calendar.freeze_active == true
}

partner_in_maintenance(partner_id) if {
    data.maintenance_windows[partner_id].active == true
}
```

### Sample Temporal Workflow (Certificate Renewal)

```python
@workflow.defn
class CertificateRenewalWorkflow:
    
    @workflow.run
    async def run(self, params: CertRenewalParams) -> CertRenewalResult:
        # Step 1: Validate current cert state
        cert_info = await workflow.execute_activity(
            fetch_cert_info,
            params.cert_id,
            start_to_close_timeout=timedelta(minutes=2)
        )
        
        # Step 2: Generate new cert via Vault PKI
        new_cert = await workflow.execute_activity(
            vault_issue_certificate,
            VaultPKIParams(
                common_name=cert_info.subject_cn,
                san=cert_info.san_list,
                ttl="8760h"
            ),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        # Step 3: Import to Axway
        import_result = await workflow.execute_activity(
            axway_import_certificate,
            AxwayImportParams(cert_pem=new_cert.certificate, partner_id=params.partner_id),
            start_to_close_timeout=timedelta(minutes=5)
        )
        
        # Step 4: Validate (synthetic HTTPS test)
        validation = await workflow.execute_activity(
            run_synthetic_https_test,
            params.partner_endpoint,
            start_to_close_timeout=timedelta(minutes=3)
        )
        
        if not validation.success:
            # Rollback: restore old cert
            await workflow.execute_activity(
                axway_import_certificate,
                AxwayImportParams(cert_pem=cert_info.original_pem, partner_id=params.partner_id),
                start_to_close_timeout=timedelta(minutes=5)
            )
            raise ApplicationError("Validation failed after cert renewal — rolled back")
        
        # Step 5: Update cert inventory, notify, close incident
        await workflow.execute_activity(
            update_cert_inventory,
            CertInventoryUpdate(cert_id=params.cert_id, new_expiry=new_cert.expiry_date)
        )
        
        return CertRenewalResult(
            success=True,
            new_cert_id=new_cert.cert_id,
            new_expiry=new_cert.expiry_date,
            validation_result=validation
        )
```

### Sample Agent Prompt: Conversational Q&A

```
Engineer: "Why do ECDSA keys fail for some partners but not others on Axway ST?"

Knowledge Agent retrieves:
  - Axway ST 5.5 docs: "Supported SSH Key Types" section
  - Runbook: "SFTP Authentication Troubleshooting"
  - 3 historical incidents involving ECDSA keys

Response:
"Based on Axway ST documentation and your incident history:

Axway SecureTransport 5.x supports ECDSA (ecdsa-sha2-nistp256, nistp384, nistp521) for **inbound** 
connections, but support for **outbound** SFTP (acting as client) depends on:

1. **Java version**: Java 7 has limited ECDSA support; Java 11+ is required for full P-384/P-521 
   curves. Your Axway instance on axway-prod-01 runs Java 11 (✓).

2. **SSH adapter cipher configuration**: The `HostKeyAlgorithms` and `PubkeyAcceptedAlgorithms` 
   settings in the Axway SSH server profile must include `ecdsa-sha2-*`. Check: 
   Admin UI → Servers → SSH Server → Advanced Settings.

3. **Known_hosts entry format**: If you scanned the partner's host key when Axway was on Java 7, 
   the known_hosts entry might be RSA even if the partner now prefers ECDSA.

In incident INC-20260112-002201, this exact pattern occurred with partner MedLogistics — their server 
only advertised nistp384, and Axway's cipher list was RSA-only. Fix: add `ecdsa-sha2-nistp384` to the 
partner's SFTP profile Host Key Algorithms field.

Want me to check your current partner configurations for this gap?"
```

---

## 26. Future Enhancements

### Near-Term (6–12 months post-launch)
- **Partner self-service portal:** Partners can upload new keys/certs, run connectivity tests, view their transfer health — dramatically reducing partner onboarding support load
- **Change impact prediction:** Before any Axway config change, AI scores risk across all partners using that config element
- **Automated runbook generation:** After each autonomously resolved incident, generate a human-readable runbook from the resolution chain and add to knowledge base

### Medium-Term (12–24 months)
- **Multi-Axway environment support:** Platform manages multiple Axway ST clusters (prod, DR, UAT) with cross-environment correlation
- **Digital twin for Axway:** Simulate configuration changes against a digital twin before applying to production
- **Vendor escalation intelligence:** When Axway product bug suspected, auto-draft Axway support case with complete diagnostic bundle, log excerpts, and suggested KB articles

### Long-Term (24+ months)
- **Natural language infrastructure:** Engineers describe desired state in natural language; AI plans and executes the configuration change with full validation
- **Cross-platform MFT intelligence:** Extend platform to cover other MFT products (IBM Sterling, GoAnywhere, MOVEit) with protocol-level knowledge transfer
- **Federated learning:** Multiple organizations running the platform can contribute (with consent) anonymized incident patterns to improve shared ML models without sharing raw data
- **MCP (Model Context Protocol) server:** Expose Axway operations as MCP tools, allowing any MCP-compatible AI assistant to securely invoke Axway operations with full audit trail

---

*Document prepared by: Principal Architecture Team*  
*Next review: 2026-08-21*  
*Status: Draft — pending engineering review*
