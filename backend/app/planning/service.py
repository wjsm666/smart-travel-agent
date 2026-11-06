"""Bridge planning to member A's shared itinerary services."""

import logging
from collections.abc import Callable
from time import monotonic
from uuid import uuid4

from app.catalog.service import list_attractions
from app.contracts import GenerationRequest, PlanInput, PlanView
from app.errors import AgentInvalidOutput, AppError, ServiceNotReady, ValidationError
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
    """Run the draft-only workflow; log stages without input or provider payloads."""
    started = monotonic()
    log = logging.LoggerAdapter(
        logging.getLogger(__name__), {"run_id": uuid4().hex, "mode": request.mode}
    )
    stage = "check_request"
    try:
        log.info("planning stage=%s", stage)
        if request.city != "汕头" or not list_attractions(city=request.city):
            raise ValidationError("当前示例数据不支持该目的地。")
        make_rule_candidate, validate_and_enrich = get_itinerary_services()

        stage = "generate_candidate"
        log.info("planning stage=%s", stage)
        if request.mode == "rules":
            draft = make_rule_candidate(request)
        else:
            candidate = await generate_candidate(request)
            draft = PlanInput(**request.model_dump(), days=candidate.days)

        stage = "validate_draft"
        log.info("planning stage=%s", stage)
        try:
            plan = validate_and_enrich(draft)
        except ValidationError as exc:
            if request.mode == "agent":
                raise AgentInvalidOutput() from exc
            raise
    except AppError as exc:
        log.warning("planning failed stage=%s code=%s", stage, exc.code)
        raise
    else:
        log.info("planning stage=draft_ready elapsed_ms=%d", (monotonic() - started) * 1000)
        return plan
