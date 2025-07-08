from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import recommend
from services.scheduler import start_scheduler
from dotenv import load_dotenv
import logging
import os

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Загрузка переменных окружения
load_dotenv()

# Печать API-ключа (для отладки, отключи в продакшене)
print("API KEY LOADED:", os.getenv("OPENAI_API_KEY"))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Настройка лимитера запросов
limiter = Limiter(key_func=get_remote_address)

# Инициализация FastAPI-приложения
app = FastAPI(
    title="Dota 2 AI Assistant",
    description="Интеллектуальный API для рекомендаций героев и билдов на основе драфта и мета-данных.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Подключение лимитера и обработчика превышения лимитов
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://твойдомен.ру"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение маршрутов
app.include_router(recommend.router)

# Запуск планировщика задач при старте приложения
@app.on_event("startup")
def on_startup():
    logging.info("API и планировщик запущены.")
    start_scheduler()

# Endpoint для проверки доступности сервиса
@app.get("/", tags=["health"])
async def root():
    return {
        "status": "ok",
        "message": "Dota 2 AI API is running.",
        "version": "1.0.0"
    }
