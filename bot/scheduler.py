from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .db import Database


def setup_scheduler(db: Database) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(db.reset_warnings, CronTrigger(day_of_week="sun", hour=0, minute=0))
    return scheduler
