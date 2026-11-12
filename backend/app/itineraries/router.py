"""Draft validation and management of saved itinerary snapshots."""

from fastapi import APIRouter, Response

from app.contracts import PlanInput, PlanView, SavedTrip
from app.itineraries import storage
from app.itineraries.service import save_trip, validate_and_enrich

router = APIRouter(prefix="/api", tags=["itineraries"])


@router.post("/plans/validate", response_model=PlanView)
def validate_plan(draft: PlanInput) -> PlanView:
    return validate_and_enrich(draft)


@router.post("/trips", status_code=201)
def create_trip(draft: PlanInput) -> SavedTrip:
    return save_trip(draft)


@router.get("/trips")
def list_trips() -> dict[str, list[SavedTrip]]:
    return {"items": storage.list_trips()}


@router.get("/trips/{trip_id}")
def get_trip(trip_id: str) -> SavedTrip:
    return storage.get_trip(trip_id)


@router.delete("/trips/{trip_id}", status_code=204)
def delete_trip(trip_id: str) -> Response:
    storage.delete_trip(trip_id)
    return Response(status_code=204)
