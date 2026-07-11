from fastapi import APIRouter, Depends

from app.config import Settings
from app.dependencies import provide_settings
from app.health import build_health
from app.schemas.health import HealthResponse

router = APIRouter(tags=["operação"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verifica a saúde dos componentes",
)
async def health(settings: Settings = Depends(provide_settings)) -> dict[str, object]:
    return build_health(settings)
