from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import UserDB
from app.schemas.user import TokenResponse, UserRead, UserRegister
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
)
from app.services.user_service import create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    if get_user_by_email(db, str(user_data.email)) is not None:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    try:
        user = create_user(db, user_data, hash_password(user_data.password))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserRead.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: UserDB = Depends(get_current_user)):
    return current_user
