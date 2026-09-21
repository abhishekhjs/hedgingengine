import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.schema import initialize_db
from backend.routers import market, exposure, transmission, montecarlo, optimization, ingestion

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    initialize_db()
    yield
    # Shutdown

app = FastAPI(
    title="IFSA Market Risk Engine API",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router)
app.include_router(exposure.router)
app.include_router(transmission.router)
app.include_router(montecarlo.router)
app.include_router(optimization.router)
app.include_router(ingestion.router)

@app.get("/")
def root():
    return {"status": "ok", "version": "1.0.0"}
