"""
Azure OpenAI client with mock fallback.

If AZURE_OPENAI_API_KEY is set in .env, calls the real Azure OpenAI API.
Otherwise returns realistic mock responses so the app is fully functional
without any API keys.
"""

from __future__ import annotations

import json
import logging

from config.settings import settings
from llm.schemas import ChatResponse, IncidentAnalysis

logger = logging.getLogger(__name__)

# ── Mock responses keyed by incident category ──────────────────────────────

_MOCK_ANALYSES: dict[str, dict] = {
    "SFTP_KEY": {
        "root_cause": "SSH host key fingerprint mismatch — the partner rotated their SFTP server key without notifying operations. Axway known_hosts still holds the old fingerprint.",
        "evidence": "Error code HOST_KEY_VERIFICATION_FAILED in sshd.log: 'WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED'",
        "confidence": 94,
        "severity": "P2",
        "fix_steps": [
            "Run ssh-keyscan -t rsa <partner_host> 22 to capture the current fingerprint",
            "Update Axway partner known_hosts via Admin API: PUT /api/v1.4/accounts/{partner_id}/sshKnownHosts",
            "Confirm the new fingerprint with the partner out-of-band",
            "Run a synthetic SFTP test (list remote directory) to validate the fix",
            "Retry any queued failed transfers",
        ],
        "auto_fixable": True,
        "auto_fix_action": "UPDATE_KNOWN_HOSTS",
        "estimated_fix_minutes": 5,
        "safety_notes": "Low risk — updating known_hosts is reversible. Pre-state is captured before change.",
        "escalate_if": "Fix fails after 2 attempts, or partner confirms they did not rotate the key (may indicate MITM attack).",
    },
    "TLS_CERT": {
        "root_cause": "SSL/TLS certificate has expired or will expire within the warning threshold. The partner's HTTPS or FTPS endpoint is rejecting connections.",
        "evidence": "Error: certificate_expired (alert code 45) during TLS ClientHello/ServerHello handshake",
        "confidence": 97,
        "severity": "P2",
        "fix_steps": [
            "Confirm certificate expiry: openssl s_client -connect <host>:<port> | openssl x509 -noout -dates",
            "Request new certificate from CA (or issue via internal PKI / Let's Encrypt)",
            "Import new certificate into Axway: POST /api/v1.4/certificates/import",
            "Assign renewed certificate to partner profile",
            "Run synthetic HTTPS connectivity test to validate TLS handshake",
        ],
        "auto_fixable": True,
        "auto_fix_action": "RENEW_CERTIFICATE",
        "estimated_fix_minutes": 15,
        "safety_notes": "Medium risk — importing certificate is reversible (old cert can be restored). Coordinate with partner if it is their certificate.",
        "escalate_if": "Certificate is partner-owned (not managed by ops). Escalate to partner to renew on their side.",
    },
    "AS2_MDN": {
        "root_cause": "AS2 MDN (Message Disposition Notification) not received within the configured timeout. Partner's MDN endpoint is unreachable or returning errors.",
        "evidence": "AS2 log: MDN-Status=pending after 300s timeout; HTTP probe to partner MDN URL returns connection refused",
        "confidence": 88,
        "severity": "P2",
        "fix_steps": [
            "Probe partner MDN endpoint: curl -I <partner_as2_mdn_url>",
            "If endpoint is down: notify partner via email/phone that their MDN listener is unreachable",
            "Switch transfer to async MDN mode as a temporary workaround",
            "Retry the failed transfer once partner confirms endpoint is restored",
            "Create ServiceNow task for partner to fix their MDN endpoint",
        ],
        "auto_fixable": False,
        "auto_fix_action": None,
        "estimated_fix_minutes": 30,
        "safety_notes": "No Axway-side changes required — issue is on partner side. Safe to retry with async MDN.",
        "escalate_if": "Partner does not respond within SLA window. Escalate to account manager.",
    },
    "JVM": {
        "root_cause": "Axway Transfer Manager JVM heap is critically high, causing frequent GC pauses that delay transfer processing and will eventually cause OutOfMemoryError.",
        "evidence": "JVM heap at 80%+ with full GC running every 30s, average pause 180ms. Thread count elevated.",
        "confidence": 91,
        "severity": "P2",
        "fix_steps": [
            "Capture thread dump immediately for post-mortem analysis: kill -3 <TM_PID>",
            "Identify top memory consumers in JVM (check for transfer log accumulation in memory)",
            "If heap > 90%: restart Transfer Manager with approval — it will resume queued transfers",
            "After restart: increase -Xmx from current value by 50% in start-tm.sh",
            "Schedule maintenance window to tune GC settings (G1GC recommended for ST 5.x)",
        ],
        "auto_fixable": True,
        "auto_fix_action": "RESTART_TRANSFER_MANAGER",
        "estimated_fix_minutes": 10,
        "safety_notes": "Restart causes ~2-5 minute transfer processing pause. Queued transfers resume automatically. Pre-state (queue snapshot) captured before action.",
        "escalate_if": "Heap reaches 95% before approval — emergency restart is justified without waiting for approval.",
    },
    "PARTNER_SILENCE": {
        "root_cause": "Partner has not sent any file transfers within their expected interval. This may indicate a problem on the partner's side, a firewall change, or a schedule change.",
        "evidence": "Last successful inbound transfer from partner was over 26 hours ago; expected interval is 6 hours.",
        "confidence": 72,
        "severity": "P3",
        "fix_steps": [
            "Check if partner has any open incidents or scheduled maintenance on their end",
            "Attempt outbound connectivity test to partner's SFTP/AS2 endpoint",
            "Review firewall change logs for the past 48 hours",
            "Contact partner operations team via SLA contact to confirm they are aware",
            "If no response: escalate to account manager",
        ],
        "auto_fixable": False,
        "auto_fix_action": None,
        "estimated_fix_minutes": 45,
        "safety_notes": "No Axway-side changes. This is a monitoring/communication issue.",
        "escalate_if": "Partner silence extends beyond 2× the SLA window, or partner cannot be reached.",
    },
    "QUEUE": {
        "root_cause": "Transfer queue depth is elevated, likely due to repeated transfer failures creating a backlog. Queued items will age and may breach SLA.",
        "evidence": "Queue depth at 47 items with oldest item 28 minutes old. Correlates with recent SFTP failures for the same partner.",
        "confidence": 85,
        "severity": "P3",
        "fix_steps": [
            "Identify root cause of the backlog (likely a separate SFTP/AS2 failure incident)",
            "Resolve the underlying failure first — do not clear the queue until the cause is fixed",
            "Once underlying issue is resolved, retry queued transfers via Admin API",
            "Monitor queue drain rate for 15 minutes to confirm recovery",
        ],
        "auto_fixable": True,
        "auto_fix_action": "RETRY_QUEUED_TRANSFERS",
        "estimated_fix_minutes": 8,
        "safety_notes": "Retrying transfers is safe. Do not clear the queue (that would discard transfers).",
        "escalate_if": "Queue continues growing after underlying issue is resolved. May indicate a secondary problem.",
    },
}

_DEFAULT_MOCK = {
    "root_cause": "Unknown failure pattern — insufficient log data to determine root cause with high confidence.",
    "evidence": "Multiple transfer failures detected without a clear error pattern.",
    "confidence": 45,
    "severity": "P3",
    "fix_steps": [
        "Collect detailed logs: enable DEBUG logging on Axway for 15 minutes",
        "Review Axway admin.log and tm.log for the failure window",
        "Check Axway service health: all adapters running?",
        "Escalate to Axway MFT operations team with log bundle",
    ],
    "auto_fixable": False,
    "auto_fix_action": None,
    "estimated_fix_minutes": 60,
    "safety_notes": "Do not take automated action when root cause is unclear.",
    "escalate_if": "Immediately — confidence is too low for autonomous remediation.",
}

_MOCK_CHAT_ANSWERS: list[str] = [
    "Based on the current system state, I can see {partner} has been experiencing issues. The most likely cause is {cause}. I recommend checking the Axway admin logs first.",
    "This pattern is commonly caused by {cause}. Here are the steps to resolve it: 1) Check the partner configuration in Axway Admin UI 2) Verify the certificate/key is still valid 3) Run a manual connectivity test.",
    "I've analyzed recent incidents and transfer logs. The {partner} failures match the pattern of {cause}. This has happened 3 times in the past 30 days — we should add a proactive check for this.",
]


# ── LLM Client ─────────────────────────────────────────────────────────────

class LLMClient:
    def __init__(self) -> None:
        self._mock = settings.mock_llm
        if not self._mock:
            from openai import AzureOpenAI
            self._client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
            logger.info("Azure OpenAI client initialized (real mode)")
        else:
            logger.info("LLM running in mock mode — set AZURE_OPENAI_API_KEY to enable real AI")

    def analyze_incident(
        self,
        category: str,
        title: str,
        description: str,
        partner_name: str = "",
        log_excerpt: str = "",
    ) -> IncidentAnalysis:
        if self._mock:
            data = _MOCK_ANALYSES.get(category, _DEFAULT_MOCK).copy()
            return IncidentAnalysis(**data)

        from agent.prompts import INCIDENT_ANALYSIS_SYSTEM
        user_content = (
            f"Incident Category: {category}\n"
            f"Title: {title}\n"
            f"Partner: {partner_name}\n"
            f"Description: {description}\n"
            f"Log excerpt:\n{log_excerpt or 'No logs available'}"
        )
        try:
            resp = self._client.chat.completions.create(
                model=settings.azure_openai_deployment_gpt4o,
                messages=[
                    {"role": "system", "content": INCIDENT_ANALYSIS_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            data = json.loads(resp.choices[0].message.content)
            return IncidentAnalysis(**data)
        except Exception as exc:
            logger.exception("Azure OpenAI call failed: %s", exc)
            return IncidentAnalysis(**_DEFAULT_MOCK)

    def chat(self, message: str, history: list[dict] | None = None) -> ChatResponse:
        if self._mock:
            answer = (
                f"(Mock AI) You asked: '{message}'. "
                "In live mode with Azure OpenAI configured, I would analyze your Axway environment "
                "and provide specific guidance. For now, check the Incidents tab for active issues, "
                "or run a manual health check using the 'Run Checks' button."
            )
            return ChatResponse(
                answer=answer,
                sources=["mock-mode"],
                follow_up_suggestions=[
                    "Show me all certificates expiring this month",
                    "Why is partner ACME failing?",
                    "What does HOST_KEY_VERIFICATION_FAILED mean?",
                ],
            )

        from agent.prompts import CHAT_SYSTEM
        messages = [{"role": "system", "content": CHAT_SYSTEM}]
        for h in (history or []):
            messages.append(h)
        messages.append({"role": "user", "content": message})

        try:
            resp = self._client.chat.completions.create(
                model=settings.azure_openai_deployment_gpt4o,
                messages=messages,
                temperature=0.3,
            )
            return ChatResponse(answer=resp.choices[0].message.content)
        except Exception as exc:
            logger.exception("Azure OpenAI chat failed: %s", exc)
            return ChatResponse(answer=f"Error contacting AI: {exc}. Check your Azure OpenAI configuration.")


llm = LLMClient()
