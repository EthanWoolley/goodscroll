from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.database import init_db
from backend.routes.projects import router as projects_router
from backend.routes.rss import router as rss_router
from backend.routes.users import router as users_router

app = FastAPI(title="Scroll API", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(users_router)
app.include_router(rss_router)


@app.on_event("startup")
def on_startup():
    init_db()
