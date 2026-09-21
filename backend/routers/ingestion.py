from fastapi import APIRouter
from typing import Dict, Any
from backend.schemas.models import IngestionStatus
from src.ingestion.runner import run_full_ingestion, check_source_connectivity

router = APIRouter(prefix="/api/ingestion", tags=["Ingestion"])

@router.post("/run", response_model=IngestionStatus)
def run_ingestion():
    status = run_full_ingestion()
    return {"status": status}

@router.get("/connectivity", response_model=Dict[str, Any])
def check_connectivity():
    return check_source_connectivity()
