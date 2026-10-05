from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import UserDB
from app.schemas.source import SourceRead
from app.schemas.user import SubscriptionRead
from app.services.auth_service import get_current_user
from app.services.source_service import get_source_by_id
from app.services.user_service import (
    get_subscription,
    get_user_sources,
    subscribe_user,
    unsubscribe_user,
)

router = APIRouter(prefix="/users/me", tags=["subscriptions"])


@router.get("/sources", response_model=list[SourceRead])
def list_my_sources(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_user_sources(db, current_user.id)


@router.post(
    "/sources/{source_id}",
    response_model=SubscriptionRead,
    status_code=201,
)
def subscribe_to_source(
    source_id: int,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if get_source_by_id(db, source_id) is None:
        raise HTTPException(status_code=404, detail="Source not found")

    return subscribe_user(db, current_user.id, source_id)


@router.delete("/sources/{source_id}")
def unsubscribe_from_source(
    source_id: int,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    subscription = get_subscription(db, current_user.id, source_id)

    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    unsubscribe_user(db, subscription)
    return {"message": "Subscription removed."}
