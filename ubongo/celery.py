import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ubongo.settings.dev")

app = Celery("ubongo")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "periodic-web-scraping": {
        "task": "blog.tasks_scraping.periodic_scraping_scheduler",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    },
    "process-content-queue": {
        "task": "blog.tasks_scraping.process_content_queue",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
    "market-monitoring": {
        "task": "blog.tasks_alerts.monitor_market_changes",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
    "scraping-health-check": {
        "task": "blog.tasks_alerts.check_scraping_health",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
    },
    "daily-market-summary": {
        "task": "blog.tasks_alerts.generate_daily_market_summary",
        "schedule": crontab(hour=0, minute=30),  # 12:30 AM daily
    },
    "cleanup-old-alerts": {
        "task": "blog.tasks_alerts.cleanup_old_alerts",
        "schedule": crontab(hour=1, minute=0),  # 1 AM daily
    },
}
