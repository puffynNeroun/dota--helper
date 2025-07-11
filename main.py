import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import recommend, builds
from services.scheduler import start_scheduler

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# === Загрузка .env ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# === Логирование ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

if not OPENAI_API_KEY:
    logging.warning("❌ OPENAI_API_KEY is not set or invalid!")
else:
    logging.info("✅ OPENAI_API_KEY loaded.")

# === Ограничение скорости запросов ===
limiter = Limiter(key_func=get_remote_address)

# === Инициализация FastAPI ===
app = FastAPI(
    title="Dota 2 AI Assistant",
    description="Интеллектуальный API для рекомендаций героев и билдов на основе драфта и мета-данных.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# === Middleware ===
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://твойдомен.ру",  # заменишь на боевой фронт
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Роутеры ===
app.include_router(recommend.router)
app.include_router(builds.router)

# === Планировщик задач ===
@app.on_event("startup")
def on_startup():
    logging.info("🚀 API запущен. Планировщик задач активирован.")
    start_scheduler()

# === Health Check ===
@app.get("/", tags=["health"])
async def root():
    return {
        "status": "ok",
        "message": "Dota 2 AI API is running.",
        "version": "1.0.0"
    }
