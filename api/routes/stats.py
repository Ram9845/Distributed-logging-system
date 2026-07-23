"""
Statistics route — aggregate analytics endpoint.

Returns comprehensive statistics about log ingestion, including
counts by level/service, latency percentiles, error rate,
throughput, and top endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from api.repository.log_repository import LogRepository
from api.services.log_service import LogService
from api.schemas.response_schema import APIResponse, StatsResponse

router = APIRouter(tags=["Statistics"])


@router.get(
    "/stats",
    response_model=APIResponse[StatsResponse],
    summary="Log Statistics",
    description="Returns aggregate statistics including total counts, "
    "breakdowns by service and level, latency percentiles, "
    "error rate, throughput, and top endpoints/errors.",
)
async def get_stats(
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    Compute and return aggregate log statistics.

    Performs multiple aggregate queries and returns a comprehensive
    statistics summary in a single response.
    """
    log_service = LogService(LogRepository(session))
    stats = await log_service.get_stats()

    return APIResponse(
        data=stats,
        message="Statistics computed successfully",
    )
