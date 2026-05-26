from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.scheduler import jobs

scheduler = AsyncIOScheduler(timezone="UTC")


def register_jobs() -> None:
    if scheduler.get_jobs():
        return
    scheduler.add_job(jobs.sync_stake_holdings, IntervalTrigger(minutes=15), id="sync_stake_holdings", replace_existing=True)
    scheduler.add_job(jobs.refresh_prices, IntervalTrigger(minutes=5), id="refresh_prices", replace_existing=True)
    scheduler.add_job(jobs.refresh_fundamentals, CronTrigger(hour=6, minute=0), id="refresh_fundamentals", replace_existing=True)
    scheduler.add_job(jobs.refresh_news, IntervalTrigger(hours=2), id="refresh_news", replace_existing=True)
    scheduler.add_job(jobs.refresh_financials, CronTrigger(day_of_week="sun", hour=2, minute=0), id="refresh_financials", replace_existing=True)
    scheduler.add_job(jobs.prune_price_history, CronTrigger(day_of_week="sat", hour=3, minute=0), id="prune_price_history", replace_existing=True)


def start_scheduler() -> None:
    register_jobs()
    if not scheduler.running:
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
