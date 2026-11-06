"""Enrich ID-only drafts using the catalog as the source of prices."""

from app.catalog.service import get_catalog
from app.contracts import Attraction, PlanDay, PlanInput, PlanView
from app.errors import ValidationError


def fits_day(items: list[Attraction]) -> bool:
    """Small planning guard shared by rule selection and draft validation."""
    return (
        len(items) <= 2
        and sum(item.duration_min or 0 for item in items) <= 480
        and not (
            any(item.area == "南澳" for item in items)
            and any(item.area != "南澳" for item in items)
        )
    )


def validate_and_enrich(draft: PlanInput) -> PlanView:
    if draft.city != "汕头":
        raise ValidationError("本版仅支持汕头。")
    if [day.day for day in draft.days] != list(range(1, draft.day_count + 1)):
        raise ValidationError("日期必须完整且按第 1 天至所选天数排列。")

    catalog = get_catalog()
    seen: set[str] = set()
    days: list[PlanDay] = []
    warnings = ["费用仅包含已知参考门票，不含交通、餐饮和住宿；资料非实时。"]
    for day in draft.days:
        items = []
        for item_id in day.attraction_ids:
            item = catalog.get(item_id)
            if item is None or item.city != draft.city:
                raise ValidationError("景点不存在或不属于汕头。")
            if item_id in seen:
                raise ValidationError("同一景点不能在行程中重复。")
            seen.add(item_id)
            items.append(item)
        if not fits_day(items):
            raise ValidationError("每天最多两处、参考游览时长最多 480 分钟，南澳须单独安排。")
        if not items:
            warnings.append(f"第 {day.day} 天暂无景点安排。")
        days.append(
            PlanDay(
                day=day.day,
                attractions=items,
                subtotal_cny=sum(item.ticket_cny for item in items if item.ticket_cny is not None),
                note=day.note,
            )
        )

    items = [item for day in days for item in day.attractions]
    total = sum(day.subtotal_cny for day in days)
    unknown = any(item.ticket_cny is None for item in items)
    over_budget = True if total > draft.budget_cny else None if unknown else False
    if unknown:
        warnings.append("部分景点票价待确认，已知门票合计不代表完整门票费用。")
    if over_budget is True:
        warnings.append("已知门票估算已超过预算。")
    if not items:
        warnings.append("草案全部为空，不能保存。")
    if draft.preferences and items:
        if not any(item.category in draft.preferences for item in items):
            warnings.append("当前安排没有匹配所选偏好的景点。")
        if any(item.category not in draft.preferences for item in items):
            warnings.append("当前安排包含非偏好类别，供用户自行调整。")
    if any(item.duration_min is None for item in items):
        warnings.append("部分参考游览时长缺失，请自行核对安排。")
    return PlanView(
        **draft.model_dump(exclude={"days"}),
        days=days,
        total_cny=total,
        has_unknown_prices=unknown,
        over_budget=over_budget,
        warnings=warnings,
    )
