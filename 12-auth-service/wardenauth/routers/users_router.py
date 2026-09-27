from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.database import get_db_session
from wardenauth.models.entities import User
from wardenauth.models.schemas import EnvelopeResponse, UserProfileUpdateRequest, UserResponse
from wardenauth.routers.dependencies import get_current_user, get_current_user_or_api_key
from wardenauth.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=EnvelopeResponse[UserResponse])
async def get_my_profile(
    current_user: User = Depends(get_current_user_or_api_key),
) -> EnvelopeResponse[UserResponse]:
    return EnvelopeResponse(data=UserResponse.model_validate(current_user))


@router.patch("/me", response_model=EnvelopeResponse[UserResponse])
async def update_my_profile(
    request_data: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[UserResponse]:
    user_service = UserService(session)
    updated_user = await user_service.update_profile(
        user_id=current_user.id,
        full_name=request_data.full_name,
    )
    return EnvelopeResponse(data=UserResponse.model_validate(updated_user))
