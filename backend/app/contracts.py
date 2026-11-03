"""Public request and response models shared with the itinerary module."""

from datetime import datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
)


def _strip_string(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


Category = Annotated[Literal["自然", "人文", "休闲"], BeforeValidator(_strip_string)]
PlanMode = Annotated[Literal["rules", "agent"], BeforeValidator(_strip_string)]
NonEmptyStr = Annotated[str, Field(min_length=1)]
Money = Annotated[StrictInt, Field(ge=0)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Attraction(ContractModel):
    id: NonEmptyStr
    city: NonEmptyStr
    name: NonEmptyStr
    category: Category
    description: NonEmptyStr
    ticket_cny: Money


class GenerationRequest(ContractModel):
    city: NonEmptyStr
    day_count: Annotated[StrictInt, Field(ge=1, le=5)]
    preferences: list[Category] = Field(default_factory=list)
    budget_cny: Money
    mode: PlanMode

    @field_validator("preferences")
    @classmethod
    def unique_preferences(cls, values: list[Category]) -> list[Category]:
        return list(dict.fromkeys(values))


class CandidateDay(ContractModel):
    day: StrictInt
    attraction_ids: list[NonEmptyStr]


class AgentCandidate(ContractModel):
    days: list[CandidateDay]


class PlanInput(GenerationRequest):
    days: list[CandidateDay]


class PlanDay(ContractModel):
    day: StrictInt
    attractions: list[Attraction]
    subtotal_cny: Money


class PlanView(GenerationRequest):
    status: Literal["draft"] = "draft"
    days: list[PlanDay]
    total_cny: Money
    over_budget: StrictBool
    warnings: list[str]


class SavedTrip(GenerationRequest):
    status: Literal["saved"] = "saved"
    days: list[PlanDay]
    total_cny: Money
    over_budget: StrictBool
    warnings: list[str]
    trip_id: NonEmptyStr
    created_at: NonEmptyStr

    @field_validator("trip_id")
    @classmethod
    def validate_trip_id(cls, value: str) -> str:
        UUID(value)
        return value

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value)
        if parsed.utcoffset() != timedelta(0):
            raise ValueError("created_at must include the UTC offset")
        return value
