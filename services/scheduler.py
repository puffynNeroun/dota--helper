from apscheduler.schedulers.background import BackgroundScheduler
from services.meta_loader import fetch_and_save_meta
import logging

# Инициализируем планировщик
scheduler = BackgroundScheduler()


def start_scheduler():
    logging.basicConfig(level=logging.INFO)
    logging.info("⏱️ Запуск планировщика: обновление мета-данных каждые 3 дня.")

    scheduler.add_job(
        fetch_and_save_meta,
        trigger="interval",
        days=3,
        id="meta_update_job",
        replace_existing=True
    )

    scheduler.start()
