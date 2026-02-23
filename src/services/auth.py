
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.auth import MessageSchema
from src.models.users import ActivationToken, RefreshToken, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


async def create_activation_token(user_id: int, db: AsyncSession) -> ActivationToken:
    user_request = await db.execute(select(User).where(User.id == user_id))
    user_response = user_request.scalar_one_or_none()

    if not user_response:
        raise HTTPException(status_code=404, detail="User not found")

    token_request = await db.execute(
        select(ActivationToken).where(ActivationToken.user_id == user_id)
    )
    token_response = token_request.scalar_one_or_none()

    if not token_response:
        activation_token = ActivationToken(user_id=user_response.id)

        try:
            db.add(activation_token)
            await db.commit()
            await db.refresh(activation_token)
        except SQLAlchemyError as e:
            print(f"Error creating activation token: {e}")

        return activation_token
    return token_response


async def check_refresh_token(user_id: int, db: AsyncSession):
    refresh_token_request = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == user_id)
    )
    refresh_token_response = refresh_token_request.scalar_one_or_none()
    if refresh_token_response:
        return refresh_token_response
    return None


async def delete_expired_refresh_token(token: RefreshToken, db: AsyncSession):
    try:
        await db.delete(token)
        await db.commit()
    except SQLAlchemyError as e:
        print(f"Error deleting expired refresh token: {e}")
    return MessageSchema(message="Delete expired token")
