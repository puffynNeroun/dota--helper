from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import recommend
from services.scheduler import start_scheduler

app = FastAPI(title="Dota 2 AI Assistant")

# Настройки CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommend.router)

# Запуск планировщика при старте
start_scheduler()

@app.get("/")
async def root():
    return {"status": "ok", "message": "Dota 2 AI API is running."}
