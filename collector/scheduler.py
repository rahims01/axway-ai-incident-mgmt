"""
APScheduler background scheduler.
Wires up all proactive check jobs on their intended intervals.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def _run_checks() -> None:
    from agent.agents import run_proactive_checks
    try:
        created = run_proactive_checks()
        if created:
            from notifications.notifier import notify_incident
            from models.database import SessionLocal
            from models.incident import Incident
            db = SessionLocal()
            try:
                for inc_id in created:
                    inc = db.query(Incident).filter(Incident.id == inc_id).first()
                    if inc:
                        notify_incident(
                            incident_number=inc.incident_number,
                            severity=inc.severity,
                            title=inc.title,
                            description=inc.description,
                            partner_name=inc.partner_name,
                            auto_fixable=bool(inc.auto_fixable),
                        )
            finally:
                db.close()
    except Exception:
        logger.exception("Scheduled check run failed")


def start() -> None:
    # High-frequency checks (every 5 min)
    scheduler.add_job(
        _run_checks,
        trigger=IntervalTrigger(minutes=5),
        id="proactive_checks",
        name="All proactive health checks",
        replace_existing=True,
        max_instances=1,  # don't pile up if a run takes long
    )

    scheduler.start()
    logger.info("Scheduler started — proactive checks every 5 minutes")

    # Run once immediately so the dashboard has data on first load
    import threading
    threading.Thread(target=_run_checks, daemon=True).start()


def stop() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
