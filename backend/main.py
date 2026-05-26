import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.firebase import init_firebase
from services import proactive
from routes import conversations, people, health, ai, relationships, scheduling, ws
from routes import proactive as proactive_routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


async def _proactive_loop():
    while True:
        await asyncio.sleep(15 * 60)
        try:
            await proactive.run()
        except Exception as e:
            logging.getLogger(__name__).error("Proactive check failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firebase()
    task = asyncio.create_task(_proactive_loop())
    yield
    task.cancel()


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
app.include_router(relationships.router, prefix="/relationships", tags=["relationships"])
app.include_router(scheduling.router, prefix="/scheduling", tags=["scheduling"])
app.include_router(proactive_routes.router, prefix="/proactive", tags=["proactive"])
app.include_router(ws.router, tags=["ws"])


@app.get("/")
async def root():
    return {"status": "aura running"}
