"""Draft-only endpoint; saving and history are intentionally not implemented yet."""

from fastapi import APIRouter

from app.contracts import PlanInput, PlanView
from app.itineraries.service import validate_and_enrich

router = APIRouter(prefix="/api", tags=["itineraries"])


@router.post("/plans/validate", response_model=PlanView)
def validate_plan(draft: PlanInput) -> PlanView:
    return validate_and_enrich(draft)
