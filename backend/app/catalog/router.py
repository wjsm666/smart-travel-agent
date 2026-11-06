"""HTTP endpoints for the shared catalog."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.catalog.service import list_attractions
from app.contracts import Attraction, Category

router = APIRouter(prefix="/api", tags=["catalog"])


class AttractionList(BaseModel):
    items: list[Attraction] = Field(default_factory=list)


@router.get("/attractions", response_model=AttractionList)
def get_attractions(
    city: str | None = None,
    keyword: str | None = None,
    category: Category | None = None,
) -> AttractionList:
    return AttractionList(items=list_attractions(city=city, keyword=keyword, category=category))
