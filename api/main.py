"""
SignalFlow — FastAPI Entry
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .routes import predictions, health

app = FastAPI(
    title="SignalFlow",
    description="Market Decision Support Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(predictions.router, prefix="/predict", tags=["predictions"])
