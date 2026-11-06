"""Bridge planning to member A's shared itinerary services."""

from collections.abc import Callable

from app.catalog.service import list_attractions
from app.contracts import GenerationRequest, PlanInput, PlanView
from app.errors import AgentInvalidOutput, ServiceNotReady, ValidationError
from app.planning.agent import generate_candidate

RuleService = Callable[[GenerationRequest], PlanInput]
ValidationService = Callable[[PlanInput], PlanView]


def get_itinerary_services() -> tuple[RuleService, ValidationService]:
    try:
        from app.itineraries.rules import make_rule_candidate
        from app.itineraries.service import validate_and_enrich
    except ModuleNotFoundError as exc:
        if exc.name in {"app.itineraries", "app.itineraries.rules", "app.itineraries.service"}:
            raise ServiceNotReady() from exc
        raise
    return make_rule_candidate, validate_and_enrich


async def generate_plan(request: GenerationRequest) -> PlanView:
    if not list_attractions(city=request.city):
        raise ValidationError("当前示例数据不支持该目的地。")

    make_rule_candidate, validate_and_enrich = get_itinerary_services()
    if request.mode == "rules":
        draft = make_rule_candidate(request)
        return validate_and_enrich(draft)

    candidate = await generate_candidate(request)
    draft = PlanInput(**request.model_dump(), days=candidate.days)
    try:
        return validate_and_enrich(draft)
    except ValidationError as exc:
        raise AgentInvalidOutput() from exc
