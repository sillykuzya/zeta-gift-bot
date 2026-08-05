from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

scheduler = AsyncIOScheduler()


def schedule_once(job_id: str, delay_seconds: int, coro_func, *args):
    """Планирует однократный запуск coro_func(*args) через delay_seconds.
    Если job с таким id уже есть — заменяет его (актуально для сброса таймеров)."""
    run_date = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
    scheduler.add_job(
        coro_func,
        trigger=DateTrigger(run_date=run_date),
        args=args,
        id=job_id,
        replace_existing=True,
        misfire_grace_time=3600,
    )


def cancel_job(job_id: str):
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass
