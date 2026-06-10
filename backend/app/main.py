"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.database import init_db
from .api.routes import (
    ai_router,
    calendar_router,
    indicators_router,
    news_router,
    sentiment_router,
    summary_router,
)

app = FastAPI(
    title="MacroAnalysis API",
    description="Macro economic indicators tracking system",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(summary_router)
app.include_router(indicators_router)
app.include_router(news_router)
app.include_router(calendar_router)
app.include_router(ai_router)
app.include_router(sentiment_router)


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}
