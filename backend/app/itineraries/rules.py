"""Deterministic baseline, without model calls or file writes."""

from app.catalog.service import list_attractions
from app.contracts import Attraction, CandidateDay, GenerationRequest, PlanInput
from app.errors import ValidationError
from app.itineraries.service import fits_day


def make_rule_candidate(request: GenerationRequest) -> PlanInput:
    if request.city != "汕头":
        raise ValidationError("本版仅支持汕头。")
    items = sorted(
        list_attractions(city=request.city),
        key=lambda item: (item.category not in request.preferences, item.id),
    )
    selected: list[list[Attraction]] = [[] for _ in range(request.day_count)]
    for item in items:
        available = [i for i, day in enumerate(selected) if fits_day([*day, item])]
        if not available:
            continue
        index = min(
            available,
            key=lambda i: (
                not any(existing.area == item.area for existing in selected[i]),
                len(selected[i]),
                i,
            ),
        )
        selected[index].append(item)
    return PlanInput(
        **request.model_dump(),
        days=[
            CandidateDay(day=i + 1, attraction_ids=[item.id for item in day])
            for i, day in enumerate(selected)
        ],
    )
