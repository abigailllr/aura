import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.firebase import init_firebase
from routes import conversations, people, health, ai

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firebase()
    yield


app = FastAPI(title="aura", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
app.include_router(people.router, prefix="/people", tags=["people"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])


@app.get("/")
async def root():
    return {"status": "aura running"}
