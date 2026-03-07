from dotenv import load_dotenv

load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.models import Base
from backend.db.session import engine
from backend.routes.feed import router as feed_router
from backend.routes.projects import router as projects_router
from backend.routes.rss import router as rss_router
from backend.routes.users import router as users_router
from backend.routes.wikipedia import router as wikipedia_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Scroll API", version="0.0.1", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feed_router)
app.include_router(projects_router)
app.include_router(users_router)
app.include_router(rss_router)
app.include_router(wikipedia_router)
