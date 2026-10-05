from sqlalchemy.orm import Session

from app.models.source import SourceDB
from app.models.user import UserDB, UserSourceDB
from app.schemas.user import UserRegister


def get_user_by_id(db: Session, user_id: int) -> UserDB | None:
    return db.query(UserDB).filter(UserDB.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> UserDB | None:
    return db.query(UserDB).filter(UserDB.email.ilike(email)).first()


def create_user(
    db: Session,
    user_data: UserRegister,
    hashed_password: str,
) -> UserDB:
    user = UserDB(
        name=user_data.name,
        email=str(user_data.email).lower(),
        hashed_password=hashed_password,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_sources(db: Session, user_id: int) -> list[SourceDB]:
    return (
        db.query(SourceDB)
        .join(UserSourceDB, UserSourceDB.source_id == SourceDB.id)
        .filter(UserSourceDB.user_id == user_id)
        .order_by(SourceDB.name.asc())
        .all()
    )


def get_subscription(
    db: Session,
    user_id: int,
    source_id: int,
) -> UserSourceDB | None:
    return (
        db.query(UserSourceDB)
        .filter(
            UserSourceDB.user_id == user_id,
            UserSourceDB.source_id == source_id,
        )
        .first()
    )


def subscribe_user(db: Session, user_id: int, source_id: int) -> UserSourceDB:
    existing = get_subscription(db, user_id, source_id)

    if existing is not None:
        return existing

    subscription = UserSourceDB(user_id=user_id, source_id=source_id)
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def unsubscribe_user(db: Session, subscription: UserSourceDB) -> None:
    db.delete(subscription)
    db.commit()
