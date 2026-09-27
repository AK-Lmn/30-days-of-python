from fastapi import APIRouter

from autoflow.engine.registry import registry
from autoflow.models.schemas import ActionCatalogItem

router = APIRouter(prefix="/actions", tags=["Actions Catalog"])


@router.get("", response_model=list[ActionCatalogItem])
async def list_available_actions() -> list[ActionCatalogItem]:
    actions = registry.list_actions()
    return [
        ActionCatalogItem(
            action_type=action.action_type,
            display_name=action.display_name,
            description=action.description,
            parameters=action.parameters_schema,
        )
        for action in actions
    ]
