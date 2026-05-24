"""
Proactive and Reactive agents.

Proactive agent: runs all health checks on a schedule, creates incidents.
Reactive agent: analyzes an existing incident with LLM and attaches RCA output.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from checks import ALL_CHECKS, Finding
from llm.client import llm
from models.database import SessionLocal
from models.incident import Incident, IncidentStatus

logger = logging.getLogger(__name__)

# In-memory fingerprint cache to avoid creating duplicate incidents within a run
# (the DB fingerprint column handles cross-run deduplication)
_seen_fingerprints: set[str] = set()


def _incident_number() -> str:
    now = datetime.now(timezone.utc)
    return f"INC-{now.strftime('%Y%m%d-%H%M%S')}"


# ── Proactive agent ────────────────────────────────────────────────────────

def run_proactive_checks() -> list[str]:
    """
    Run all health checks and persist new findings as incidents.
    Returns a list of created incident IDs.
    """
    logger.info("Running proactive health checks…")
    findings: list[Finding] = []

    for check_fn in ALL_CHECKS:
        try:
            results = check_fn()
            findings.extend(results)
            logger.debug("  %s → %d finding(s)", check_fn.__name__, len(results))
        except Exception:
            logger.exception("Check %s raised an exception", check_fn.__name__)

    logger.info("Proactive checks complete — %d finding(s) total", len(findings))

    created_ids: list[str] = []
    db = SessionLocal()
    try:
        for finding in findings:
            # DB-level deduplication: skip if open incident with same fingerprint exists
            existing = (
                db.query(Incident)
                .filter(
                    Incident.fingerprint == finding.fingerprint,
                    Incident.status.notin_([IncidentStatus.RESOLVED, IncidentStatus.ESCALATED]),
                )
                .first()
            )
            if existing:
                logger.debug("Skipping duplicate finding %s (existing: %s)", finding.fingerprint, existing.incident_number)
                continue

            incident = Incident(
                incident_number=_incident_number(),
                category=finding.category,
                severity=finding.severity,
                status=IncidentStatus.NEW,
                partner_id=finding.partner_id,
                partner_name=finding.partner_name,
                protocol=finding.protocol,
                title=finding.title,
                description=finding.description,
                source_check=finding.check_name,
                fingerprint=finding.fingerprint,
                raw_data=finding.raw_data,
            )
            db.add(incident)
            db.commit()
            db.refresh(incident)
            created_ids.append(incident.id)
            logger.info("Created incident %s [%s] %s", incident.incident_number, incident.severity, incident.title[:60])
    finally:
        db.close()

    return created_ids


# ── Reactive agent ─────────────────────────────────────────────────────────

def analyze_incident(incident_id: str) -> Incident | None:
    """
    Run LLM root-cause analysis on an incident and update it in the DB.
    Returns the updated Incident or None if not found.
    """
    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None

        incident.status = IncidentStatus.ANALYZING
        db.commit()

        logger.info("Analyzing incident %s with LLM…", incident.incident_number)
        analysis = llm.analyze_incident(
            category=incident.category,
            title=incident.title,
            description=incident.description,
            partner_name=incident.partner_name or "",
        )

        incident.root_cause = analysis.root_cause
        incident.confidence = analysis.confidence
        incident.fix_steps = analysis.fix_steps
        incident.auto_fixable = analysis.auto_fixable
        incident.auto_fix_action = analysis.auto_fix_action
        incident.status = IncidentStatus.NEW  # back to NEW — awaiting action decision
        db.commit()
        db.refresh(incident)
        logger.info(
            "Analysis complete for %s — confidence %d%%, auto_fixable=%s",
            incident.incident_number, analysis.confidence, analysis.auto_fixable,
        )
        return incident
    finally:
        db.close()


# ── Auto-fix dispatcher ────────────────────────────────────────────────────

def attempt_auto_fix(incident_id: str) -> dict:
    """
    Attempt an automated fix for an incident. Only executes safe actions.
    Returns a result dict with status and message.
    """
    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return {"status": "ERROR", "message": "Incident not found"}

        if not incident.auto_fixable:
            return {"status": "SKIPPED", "message": "Incident is not marked as auto-fixable"}

        if not incident.auto_fix_action:
            return {"status": "SKIPPED", "message": "No auto-fix action defined"}

        from actions.axway_actions import dispatch_action
        incident.status = IncidentStatus.REMEDIATING
        db.commit()

        result = dispatch_action(
            action=incident.auto_fix_action,
            incident=incident,
        )

        if result.get("success"):
            incident.status = IncidentStatus.RESOLVED
            incident.resolved_at = datetime.now(timezone.utc)
            incident.resolution_notes = result.get("message", "Auto-fixed successfully")
        else:
            incident.status = IncidentStatus.ESCALATED
            incident.resolution_notes = f"Auto-fix failed: {result.get('message')}"

        db.commit()
        return result
    finally:
        db.close()
