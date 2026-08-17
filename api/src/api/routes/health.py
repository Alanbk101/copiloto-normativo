from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    postgres: Literal["ok", "error"]
    redis: Literal["ok", "error"]


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request, response: Response) -> HealthResponse:
    postgres_status: Literal["ok", "error"] = "error"
    redis_status: Literal["ok", "error"] = "error"

    try:
        async with request.app.state.db_session_factory() as session:
            await session.execute(text("SELECT 1"))
        postgres_status = "ok"
    except Exception:
        postgres_status = "error"

    try:
        pong = await request.app.state.redis.ping()
        if pong:
            redis_status = "ok"
    except Exception:
        redis_status = "error"

    overall_status: Literal["ok", "degraded"] = (
        "ok" if postgres_status == "ok" and redis_status == "ok" else "degraded"
    )

    if overall_status == "degraded":
        response.status_code = 503

    return HealthResponse(
        status=overall_status,
        postgres=postgres_status,
        redis=redis_status,
    )
