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
        "schedule": crontab(),
    },
    "process-content-queue": {
        "task": "blog.tasks_scraping.process_content_queue",
        "schedule": crontab(),
    },
}
