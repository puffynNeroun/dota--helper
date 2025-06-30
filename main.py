from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import recommend
from services.scheduler import start_scheduler
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


app = FastAPI(
    title="Dota 2 AI Assistant",
    description="API для рекомендаций героев и билдов в Dota 2 на основе мета-данных",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(recommend.router)


@app.on_event("startup")
def on_startup():
    logging.info("🚀 Запуск API и планировщика задач...")
    start_scheduler()


@app.get("/", tags=["health"])
async def root():
    return {
        "status": "ok",
        "message": "✅ Dota 2 AI API is running.",
        "version": "1.0.0"
    }
