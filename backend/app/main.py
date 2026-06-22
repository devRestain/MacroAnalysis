"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes.ai import router as ai_router
from .api.routes.calendar import router as calendar_router
from .api.routes.indicators import router as indicators_router
from .api.routes.news import router as news_router
from .api.routes.sentiment import router as sentiment_router
from .api.routes.summary import router as summary_router
from .core.config import settings
from .core.database import init_db

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
