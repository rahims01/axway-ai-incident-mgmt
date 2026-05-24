"""
Unified notification dispatcher.

Sends to Slack and/or Teams when configured, otherwise logs to console.
ServiceNow ticket creation is a placeholder — implement when you have API access.
"""

from __future__ import annotations

import json
import logging

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

SEV_EMOJI = {"P1": "🔴", "P2": "🟠", "P3": "🟡", "P4": "🔵"}


def notify_incident(
    incident_number: str,
    severity: str,
    title: str,
    description: str,
    partner_name: str | None = None,
    auto_fixable: bool = False,
) -> None:
    emoji = SEV_EMOJI.get(severity, "⚪")
    text = (
        f"{emoji} *[{severity}] {incident_number}*\n"
        f"*{title}*\n"
        f"{description[:300]}"
        + (f"\n_Partner: {partner_name}_" if partner_name else "")
        + ("\n✅ Auto-fix available" if auto_fixable else "")
    )

    _log_to_console(severity, incident_number, title)

    if settings.slack_enabled:
        _send_slack(settings.slack_alert_channel, text)

    if settings.teams_enabled:
        _send_teams(title, description, severity)


def notify_resolved(incident_number: str, resolution: str) -> None:
    logger.info("✅ RESOLVED %s — %s", incident_number, resolution[:100])
    if settings.slack_enabled:
        _send_slack(settings.slack_alert_channel, f"✅ *{incident_number} RESOLVED*\n{resolution[:200]}")


def request_approval(
    incident_number: str,
    severity: str,
    title: str,
    proposed_action: str,
) -> None:
    """Post an approval request to the ops channel."""
    text = (
        f"🔔 *APPROVAL REQUIRED — {incident_number} [{severity}]*\n"
        f"*Incident:* {title}\n"
        f"*Proposed action:* `{proposed_action}`\n"
        "Reply ✅ to approve or ❌ to reject."
    )
    logger.info("APPROVAL REQUEST %s: %s → %s", incident_number, title, proposed_action)
    if settings.slack_enabled:
        _send_slack(settings.slack_approval_channel, text)


def create_servicenow_ticket(incident_number: str, title: str, description: str) -> str | None:
    """
    Create a ServiceNow incident ticket.
    PLACEHOLDER — implement when ServiceNow API credentials are available.
    """
    if not settings.servicenow_enabled:
        logger.info("[ServiceNow PLACEHOLDER] Would create ticket for %s: %s", incident_number, title)
        return None

    # PLACEHOLDER: POST to ServiceNow table API
    # url = f"{settings.servicenow_url}/api/now/table/incident"
    # resp = httpx.post(url, auth=(settings.servicenow_user, settings.servicenow_password),
    #                   json={"short_description": title, "description": description,
    #                         "urgency": "2", "impact": "2"})
    # return resp.json()["result"]["sys_id"]
    logger.info("[ServiceNow PLACEHOLDER] ServiceNow configured but not yet implemented — %s", incident_number)
    return None


# ── Internal helpers ───────────────────────────────────────────────────────

def _log_to_console(severity: str, number: str, title: str) -> None:
    emoji = SEV_EMOJI.get(severity, "⚪")
    logger.info("%s INCIDENT %s [%s] %s", emoji, number, severity, title)


def _send_slack(channel: str, text: str) -> None:
    try:
        resp = httpx.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
            json={"channel": channel, "text": text, "mrkdwn": True},
            timeout=10,
        )
        data = resp.json()
        if not data.get("ok"):
            logger.warning("Slack send failed: %s", data.get("error"))
    except Exception as exc:
        logger.warning("Slack notification failed: %s", exc)


def _send_teams(title: str, description: str, severity: str) -> None:
    # Teams Incoming Webhook (Adaptive Card format)
    payload = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {"type": "TextBlock", "text": f"[{severity}] Axway AIOps Alert", "weight": "Bolder"},
                    {"type": "TextBlock", "text": title, "wrap": True},
                    {"type": "TextBlock", "text": description[:500], "wrap": True, "isSubtle": True},
                ],
            },
        }],
    }
    try:
        httpx.post(settings.teams_webhook_url, json=payload, timeout=10)
    except Exception as exc:
        logger.warning("Teams notification failed: %s", exc)
