# Axway SecureTransport — AI Incident Management Platform
## Simplified Design

---

## What This System Does

Monitors your Axway SecureTransport environment continuously, spots problems before clients report them, diagnoses the root cause automatically, and either fixes it or tells your team exactly what to do.

---

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│              AXWAY SECURE TRANSPORT                      │
│  Logs  │  Admin API  │  Transfer DB  │  Metrics          │
└──────────────────────┬──────────────────────────────────┘
                       │ poll every 60s
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  COLLECTOR SERVICE                        │
│  Reads Axway logs + API, normalizes events               │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  AI AGENT (3 modes)                      │
│                                                          │
│  [PROACTIVE]  Scans health every 15 min                  │
│    - cert expiry check                                   │
│    - SSH key validity                                    │
│    - transfer failure rate trending up?                  │
│    - partner last-seen > expected interval?              │
│                                                          │
│  [REACTIVE]   Triggered by failure event                 │
│    - calls Azure OpenAI with log context                 │
│    - produces root cause + recommended fix               │
│                                                          │
│  [CHAT]       Engineer asks questions                    │
│    - "why is partner X failing?"                         │
│    - "show me all certs expiring this month"             │
└──────────────────────┬──────────────────────────────────┘
                       │
              ┌────────┴─────────┐
              ▼                  ▼
┌─────────────────────┐  ┌───────────────────────────┐
│  NOTIFICATION       │  │  AUTO-FIX (optional)       │
│  Slack / Teams /    │  │  retry transfer            │
│  Email / ServiceNow │  │  clear stuck queue         │
└─────────────────────┘  │  schedule cert renewal     │
                         └───────────────────────────┘
```

---

## The Three Core Components

### 1. Collector Service
A lightweight Python service that runs on-prem (or close to Axway):

```
What it collects (every 60 seconds):
  ✓ Failed transfers in last 60s  → via Axway Admin API
  ✓ New log lines                 → tail Axway log files
  ✓ Current service status        → Admin API /services
  ✓ Cert expiry dates             → Admin API /certs
  ✓ Transfer queue depths         → Admin API /queues

What it stores:
  → PostgreSQL: normalized events, incident history
  → Redis: rate counters, dedup cache (5-min window)
```

### 2. AI Agent (Azure OpenAI GPT-4o)

Three operating modes, all using the same Azure OpenAI endpoint:

**Mode A — Proactive Health Check (every 15 min)**
```python
checks = [
    check_cert_expiry(),         # any cert expiring in < 30 days?
    check_transfer_failure_rate(),# failure rate > baseline by 20%?
    check_partner_silence(),      # partner hasn't sent a file when expected?
    check_ssh_keys(),             # any keys older than 1 year or weak algo?
    check_queue_depth(),          # any queue growing without draining?
    check_disk_space(),           # Axway data partition > 80%?
    check_jvm_heap(),             # JVM heap > 85%?
]
# Any check triggers an alert with AI-generated context
```

**Mode B — Reactive Incident Analysis (on failure event)**
```
Trigger: ≥3 failed transfers for same partner in 5 min
         OR any P1/P2 alert from monitoring

Steps:
1. Fetch last 50 log lines for that partner/protocol
2. Send to GPT-4o with Axway-expert system prompt
3. Get back: root cause, confidence, fix steps
4. Post to Slack/Teams immediately
5. Create ServiceNow ticket (optional)
6. Execute safe auto-fixes if confidence > 85%
```

**Mode C — Chat Interface (Slack bot / Teams bot)**
```
Engineer: "@axway-bot why is ACME failing?"
Bot: fetches live data → calls GPT-4o → responds in < 10s

Engineer: "@axway-bot list certs expiring in June"
Bot: queries cert inventory → formats answer (no LLM needed)

Engineer: "@axway-bot run diagnostics on partner GLOBALCO"
Bot: runs full check → LLM summarizes findings
```

### 3. Action Layer

**Safe auto-fixes (no approval needed):**
- Retry a failed transfer
- Clear a stuck queue
- Send partner notification email
- Create ServiceNow / Jira ticket

**Fixes requiring Slack approval (one-click):**
- Update SSH known_hosts with new key fingerprint
- Restart Axway listener service
- Import renewed certificate

**Fixes that always need a human:**
- Partner configuration changes
- CA certificate changes
- Firewall/network changes

---

## What Gets Detected Proactively

| Check | Frequency | Alert Lead Time |
|---|---|---|
| SSL cert expiry | Every 15 min | 30 / 15 / 7 / 1 day warning |
| SSH key weak algorithm (RSA < 2048, DSA) | Daily | Immediate flag |
| SSH key rotation (partner changed key) | Every 5 min | Same minute |
| Transfer failure rate spike | Every 5 min | Minutes before SLA breach |
| Partner silence (no transfer when expected) | Every 15 min | Before client notices |
| Axway disk usage > 80% | Every 15 min | Hours before service impact |
| JVM heap > 85% | Every 5 min | Before OOM crash |
| AS2 MDN not received | Every 5 min | Within 10 min of MDN timeout |
| Cipher suite incompatibility | On failure | Immediate |
| Transfer queue growing | Every 5 min | Before backlog causes SLA miss |

---

## Azure OpenAI Integration

**Models used:**
- `gpt-4o` — incident analysis, root cause reasoning, chat
- `gpt-4o-mini` — cert expiry summaries, simple classification, high-volume event tagging

**System prompt for incident analysis:**
```
You are an expert Axway SecureTransport MFT operations engineer.
You diagnose file transfer incidents involving SFTP (RSA/ECDSA keys),
AS2, HTTPS/SSL certificates, and FTPS.

When given log excerpts and partner context, you:
1. Identify the root cause (be specific — cite the log line)
2. Rate your confidence (0–100%)
3. List the exact fix steps in order
4. Flag any safety concerns with the fix
5. Estimate time to fix

Always respond in JSON. Never suggest destructive actions.
If unsure, say so and recommend human review.
```

**Example call:**
```python
response = await openai_client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": AXWAY_EXPERT_SYSTEM_PROMPT},
        {"role": "user", "content": f"""
Partner: {partner_name} ({partner_id})
Protocol: SFTP
Failure count: {failure_count} in last 5 minutes
Last success: {last_success}

Recent log lines:
{log_excerpt}

Partner config:
{partner_config_summary}

Diagnose this incident and provide fix steps.
        """}
    ],
    response_format={"type": "json_object"},
    temperature=0.1  # low temperature for consistent, factual output
)
```

---

## Data Flow for a Typical Incident

```
12:01:00  Partner ACME starts failing SFTP transfers
12:01:00  Collector detects 1st failure via Axway API
12:03:00  3rd failure in 5 min → threshold crossed
12:03:05  Collector fetches last 50 ACME log lines
12:03:06  GPT-4o called with log context
12:03:09  Response: "SSH host key changed. Old: SHA256:abc, New: SHA256:xyz.
           Confidence: 94%. Fix: update known_hosts in Axway partner config."
12:03:10  Slack message posted to #mft-alerts:
           "🔴 ACME SFTP failing (3 failures, 5 min)
            Root cause: SSH host key changed
            Fix: Update known_hosts [✅ Auto-fix] [📋 View Details]"
12:04:30  Engineer clicks ✅ Auto-fix
12:04:35  Axway Admin API: known_hosts updated
12:04:40  Synthetic SFTP test → success
12:04:41  Slack: "✅ Fixed. ACME SFTP restored. Validation passed."
Total time: 3 min 41 sec
```

---

## Tech Stack (Simple)

| Component | Technology | Why |
|---|---|---|
| Language | Python 3.12 | Best AI/LLM ecosystem |
| LLM | Azure OpenAI (GPT-4o + GPT-4o-mini) | Your existing MS contract |
| AI framework | LangChain (minimal) | Simple chain + tool calling |
| Scheduler | APScheduler | Built-in Python, no extra infra |
| Database | PostgreSQL | Incidents, cert inventory, history |
| Cache | Redis | Dedup, rate counters, session |
| API | FastAPI | REST API + webhook receiver |
| Slack bot | Slack Bolt SDK | Interactive approvals |
| Teams bot | Bot Framework SDK | If Teams preferred |
| Deployment | Docker Compose (start) → K8s (scale) | Start simple |
| Monitoring | Grafana + Prometheus (optional) | Basic dashboards |

---

## Project Structure

```
axway-incident-ai-agent/
├── collector/
│   ├── axway_client.py      # Axway Admin API wrapper
│   ├── log_tailer.py        # Tail Axway log files
│   ├── normalizer.py        # Raw events → NormalizedEvent
│   └── scheduler.py         # APScheduler jobs
│
├── agent/
│   ├── proactive.py         # Health check agent (15-min loop)
│   ├── reactive.py          # Incident analysis agent (on-event)
│   ├── chat.py              # Conversational interface
│   └── prompts.py           # All system prompts
│
├── llm/
│   ├── client.py            # Azure OpenAI client wrapper
│   └── schemas.py           # Pydantic output schemas for LLM responses
│
├── actions/
│   ├── safe_actions.py      # Auto-executable fixes
│   ├── approval_actions.py  # Slack-approval-required fixes
│   └── axway_actions.py     # Axway API mutating calls
│
├── notifications/
│   ├── slack.py             # Slack alerts + interactive messages
│   ├── teams.py             # Teams alerts
│   └── servicenow.py        # Ticket creation
│
├── checks/                  # One file per proactive check
│   ├── cert_expiry.py
│   ├── transfer_failures.py
│   ├── partner_silence.py
│   ├── ssh_keys.py
│   ├── queue_depth.py
│   └── jvm_health.py
│
├── models/
│   └── incident.py          # SQLAlchemy models
│
├── api/
│   └── main.py              # FastAPI: webhooks, chat endpoint
│
├── config/
│   └── settings.py          # Pydantic Settings (env-based)
│
├── docker-compose.yml
└── .env.example
```

---

## Configuration (.env)

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT_GPT4O=gpt-4o
AZURE_OPENAI_DEPLOYMENT_MINI=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Axway SecureTransport
AXWAY_ADMIN_URL=https://axway-host:444
AXWAY_ADMIN_USER=admin
AXWAY_ADMIN_PASSWORD=secret
AXWAY_LOG_PATH=/opt/axway/SecureTransport/var/log

# Database
DATABASE_URL=postgresql://aiops:secret@localhost:5432/axway_aiops
REDIS_URL=redis://localhost:6379

# Notifications
SLACK_BOT_TOKEN=xoxb-...
SLACK_ALERT_CHANNEL=#mft-alerts
SLACK_APPROVAL_CHANNEL=#mft-ops

# Thresholds
CERT_EXPIRY_WARN_DAYS=30
FAILURE_RATE_THRESHOLD=3         # failures per 5-min window
QUEUE_DEPTH_WARN=1000
JVM_HEAP_WARN_PCT=85
DISK_WARN_PCT=80
AUTO_FIX_CONFIDENCE_THRESHOLD=85
```

---

## Implementation Phases

### Phase 1 — See Everything (Week 1–2)
- [ ] Axway API collector running
- [ ] Cert expiry check with Slack alerts
- [ ] Transfer failure rate alerts
- [ ] Basic dashboard (how many failures, by partner, by protocol)

### Phase 2 — Understand Why (Week 3–4)
- [ ] Reactive incident analysis with GPT-4o
- [ ] Root cause posted to Slack with fix steps
- [ ] ServiceNow ticket auto-creation
- [ ] Incident history in PostgreSQL

### Phase 3 — Fix Automatically (Week 5–6)
- [ ] Safe auto-fixes: transfer retry, queue clear
- [ ] Approval-gated fixes: known_hosts update, service restart
- [ ] Synthetic test validation after each fix
- [ ] Rollback on failed validation

### Phase 4 — Predict & Prevent (Week 7–8)
- [ ] Partner silence detection (SLA-aware schedule)
- [ ] Transfer throughput trend (is failure rate slowly climbing?)
- [ ] Chat interface: "@axway-bot diagnose partner X"
- [ ] Weekly health report auto-generated by GPT-4o

---

## Incident Output Format (GPT-4o response schema)

```json
{
  "root_cause": "SSH host key fingerprint mismatch — partner rotated their RSA key",
  "evidence": "sshd.log 12:01:33 — 'Host key verification failed' for ACME@sftp.acme.com",
  "confidence": 94,
  "severity": "P2",
  "fix_steps": [
    "Run: ssh-keyscan -t rsa sftp.acme.com to get new fingerprint",
    "Update Axway partner ACME known_hosts via Admin API",
    "Run synthetic SFTP test to validate"
  ],
  "auto_fixable": true,
  "auto_fix_action": "UPDATE_KNOWN_HOSTS",
  "estimated_fix_minutes": 3,
  "safety_notes": "Low risk — reverting is trivial if wrong key captured",
  "escalate_if": "Fix fails after 2 attempts — may indicate partner IP change or firewall block"
}
```

---

## Estimated Infrastructure Cost

| Item | Monthly Cost |
|---|---|
| Azure OpenAI GPT-4o (500 incidents/month) | ~$50–150 |
| GPT-4o-mini (proactive checks, tagging) | ~$10–30 |
| 2× small VMs (collector + agent) | ~$100–200 |
| PostgreSQL (managed) | ~$50–100 |
| Redis (managed) | ~$30–60 |
| **Total** | **~$240–540/month** |

Compare to: 1 engineer-hour of incident work ≈ $100–150 at loaded cost.
Saving 10 hours/month pays for the whole platform.
