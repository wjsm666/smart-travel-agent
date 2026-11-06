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
    model_validator,
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
    ticket_cny: Money | None
    area: NonEmptyStr = "待补充"
    duration_min: Annotated[StrictInt, Field(gt=0, le=480)] | None = None
    source_url: str | None = None
    ticket_source_url: str | None = None
    ticket_checked_at: str | None = None
    ticket_note: str | None = None


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
    note: Annotated[str, Field(max_length=240)] | None = None


class AgentCandidate(ContractModel):
    days: list[CandidateDay]


class PlanInput(GenerationRequest):
    days: list[CandidateDay]


class PlanDay(ContractModel):
    day: StrictInt
    attractions: list[Attraction]
    subtotal_cny: Money
    note: Annotated[str, Field(max_length=240)] | None = None


def _validate_ticket_summary(
    days: list[PlanDay], total: int, budget: int, unknown: bool, over_budget: bool | None
) -> None:
    calculated_total = 0
    calculated_unknown = False
    for day in days:
        known_prices = [item.ticket_cny for item in day.attractions if item.ticket_cny is not None]
        if sum(known_prices) != day.subtotal_cny:
            raise ValueError("daily ticket subtotal does not match known prices")
        calculated_total += day.subtotal_cny
        calculated_unknown |= any(item.ticket_cny is None for item in day.attractions)
    expected_over = True if calculated_total > budget else None if calculated_unknown else False
    if calculated_total != total or calculated_unknown != unknown or over_budget != expected_over:
        raise ValueError("ticket budget summary is inconsistent")


class PlanView(GenerationRequest):
    status: Literal["draft"] = "draft"
    days: list[PlanDay]
    total_cny: Money
    over_budget: StrictBool | None
    has_unknown_prices: StrictBool = False
    warnings: list[str]

    @model_validator(mode="after")
    def check_ticket_summary(self):
        _validate_ticket_summary(
            self.days, self.total_cny, self.budget_cny, self.has_unknown_prices, self.over_budget
        )
        return self


class SavedTrip(GenerationRequest):
    status: Literal["saved"] = "saved"
    days: list[PlanDay]
    total_cny: Money
    over_budget: StrictBool | None
    has_unknown_prices: StrictBool = False
    warnings: list[str]
    trip_id: NonEmptyStr
    created_at: NonEmptyStr

    @model_validator(mode="after")
    def check_ticket_summary(self):
        _validate_ticket_summary(
            self.days, self.total_cny, self.budget_cny, self.has_unknown_prices, self.over_budget
        )
        return self

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
