"""Planning endpoint; no persistence takes place here."""

from fastapi import APIRouter

from app.contracts import GenerationRequest, PlanView
from app.planning.service import generate_plan

router = APIRouter(prefix="/api/plans", tags=["planning"])


@router.post("/generate", response_model=PlanView)
async def generate(request: GenerationRequest) -> PlanView:
    return await generate_plan(request)
