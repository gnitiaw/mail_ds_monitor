from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import admin_required, db_session
from app.models.user import User
from app.schemas.common import success
from app.schemas.service_report import UserOptionResponse, UserOptionsListResponse

router = APIRouter(prefix="/users")


@router.get("/options")
def list_user_options(
    db: Annotated[Session, Depends(db_session)],
    _: Annotated[User, Depends(admin_required)],
) -> dict:
    users = list(db.scalars(select(User).where(User.is_active == True).order_by(User.display_name.asc())).all())
    data = UserOptionsListResponse(
        items=[
            UserOptionResponse(id=user.id, display_name=user.display_name, role=user.role)
            for user in users
        ]
    )
    return success(data.model_dump())
