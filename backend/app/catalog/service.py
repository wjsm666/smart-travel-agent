"""Read and filter the local, intentionally fictional attraction catalog."""

import json

from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError

from app.config import get_settings
from app.contracts import Attraction
from app.errors import StorageError


def get_catalog() -> dict[str, Attraction]:
    path = get_settings().resolve_data_path(get_settings().attractions_path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = TypeAdapter(list[Attraction]).validate_python(raw)
    except (OSError, UnicodeError, ValueError, PydanticValidationError) as exc:
        raise StorageError() from exc

    catalog = {item.id: item for item in items}
    if len(catalog) != len(items):
        raise StorageError("示例景点编号重复，请检查本地数据文件。")
    return catalog


def list_attractions(
    city: str | None = None,
    keyword: str | None = None,
    category: str | None = None,
) -> list[Attraction]:
    if city is not None:
        city = city.strip()
    if keyword is not None:
        keyword = keyword.strip()
    if category is not None:
        category = category.strip()
    items = get_catalog().values()
    return sorted(
        (
            item
            for item in items
            if (city is None or item.city == city)
            and (category is None or item.category == category)
            and (keyword is None or keyword in item.name or keyword in item.description)
        ),
        key=lambda item: item.id,
    )
