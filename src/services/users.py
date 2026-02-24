from fastapi import HTTPException
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.users import UserReadSchema, UserRegisterSchema
from security.password import hash_password
from security.token_manager import decode_token
from services.auth import create_activation_token, oauth2_scheme
from services.email import send_activation_email
from src.models.users import User


async def create_user(user: UserRegisterSchema, db: AsyncSession) -> User:
    hashed_password = hash_password(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password, group_id=1)

    try:
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
    except SQLAlchemyError as e:
        print(f"Error creating user: {e}")
    except Exception as e:
        print(f"Error creating user: {e}")

    activation_token = await create_activation_token(db_user.id, db=db)

    if db_user and activation_token:
        send_activation_email(db_user.email, activation_token.token)
    return db_user


async def get_user_by_email(email: str, db: AsyncSession) -> User:
    user_request = await db.execute(select(User).where(User.email == email))
    user_response = user_request.scalar_one_or_none()

    return user_response


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    email = payload.get("subject")
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid token email")
    db_user = await get_user_by_email(email=email, db=db)

    return UserReadSchema(id=db_user.id, email=db_user.email)


async def check_user(email: str, db: AsyncSession) -> bool:
    if await get_user_by_email(email=email, db=db) is None:
        raise HTTPException(status_code=404, detail="User not found")


async def check_admin(email: str, db: AsyncSession) -> bool:
    user = await get_user_by_email(email=email, db=db)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    print(user)
    if user.group_id == 3:
        return True
    return False
