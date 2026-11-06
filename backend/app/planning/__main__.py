"""Local, draft-only entry point: python -m app.planning --mode rules."""

import argparse
import asyncio
import json
import logging

from pydantic import ValidationError as PydanticValidationError

from app.contracts import GenerationRequest
from app.errors import AppError
from app.planning.service import generate_plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成汕头行程草案，不保存文件")
    parser.add_argument("--mode", choices=["rules", "agent"], default="rules")
    parser.add_argument("--days", type=int, default=2)
    parser.add_argument("--budget", type=int, default=100)
    parser.add_argument(
        "--preference", choices=["自然", "人文", "休闲"], action="append", default=[]
    )
    args = parser.parse_args(argv)
    try:
        request = GenerationRequest(
            city="汕头",
            day_count=args.days,
            preferences=args.preference,
            budget_cny=args.budget,
            mode=args.mode,
        )
    except PydanticValidationError:
        print(
            json.dumps(
                {"code": "VALIDATION_ERROR", "message": "天数须为 1–5，预算须非负。"},
                ensure_ascii=False,
            )
        )
        return 1
    try:
        plan = asyncio.run(generate_plan(request))
    except AppError as exc:
        print(json.dumps({"code": exc.code, "message": exc.message}, ensure_ascii=False))
        return 1
    print(plan.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    # Only the local CLI configures logging; imported services leave it to the host.
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(levelname)s run=%(run_id)s mode=%(mode)s %(message)s")
    )
    logger = logging.getLogger("app.planning.service")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    raise SystemExit(main())
