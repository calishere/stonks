from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "stonks",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.scheduled_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,  # One task at a time for data fetching
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Refresh stock list daily at 6:00 AM UTC
    "refresh-stock-list": {
        "task": "app.tasks.scheduled_tasks.refresh_stock_list",
        "schedule": crontab(hour=6, minute=0),
    },
    # Update prices daily at 6:30 AM UTC (after market close)
    "update-prices": {
        "task": "app.tasks.scheduled_tasks.update_all_prices",
        "schedule": crontab(hour=6, minute=30),
    },
    # Update financials weekly on Sundays at 7:00 AM UTC
    "update-financials": {
        "task": "app.tasks.scheduled_tasks.update_all_financials",
        "schedule": crontab(hour=7, minute=0, day_of_week=0),
    },
    # Recalculate metrics daily at 7:30 AM UTC
    "recalculate-metrics": {
        "task": "app.tasks.scheduled_tasks.recalculate_all_metrics",
        "schedule": crontab(hour=7, minute=30),
    },
    # Update valuations daily at 8:00 AM UTC
    "update-valuations": {
        "task": "app.tasks.scheduled_tasks.update_all_valuations",
        "schedule": crontab(hour=8, minute=0),
    },
}
