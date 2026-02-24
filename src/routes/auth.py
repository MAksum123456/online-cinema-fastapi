import datetime
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.auth import (
    AccessTokenSchema,
    ActivationAccountSchema,
    ChangePasswordRequestSchema,
    EmailSchema,
    MessageSchema,
    RefreshTokenSchema,
    ResendActivationAccountSchema,
    ResetPasswordSchema,
)
from schemas.users import (
    UserLoginRequestSchema,
    UserLoginResponseSchema,
    UserReadSchema,
    UserRegisterSchema,
)
from security.password import hash_password, verify_password
from security.token_manager import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from services.auth import (
    check_refresh_token,
    delete_expired_refresh_token,
    oauth2_scheme,
)
from services.email import send_activation_email, send_reset_password_email
from services.users import (
    check_user,
    create_activation_token,
    create_user,
    get_user_by_email,
)
from src.models.users import ActivationToken, PasswordResetToken, RefreshToken
from validation.password import validate_password_strength

router = APIRouter()


@router.post("/register", response_model=UserReadSchema)
async def register(user: UserRegisterSchema, db: AsyncSession = Depends(get_db)):
    try:

        user_request = await get_user_by_email(email=user.email, db=db)

        if user_request:
            raise HTTPException(status_code=400, detail="Email already registered")

        validate_password_strength(password=user.password)

        new_user = await create_user(user=user, db=db)

        return new_user
    except Exception as e:
        print(e)


@router.post("/activate/{token}", response_model=MessageSchema)
async def activate(
    activation_data: ActivationAccountSchema, db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_email(email=activation_data.email, db=db)
    await check_user(activation_data.email, db=db)

    token_request = await db.execute(
        select(ActivationToken).where(ActivationToken.user_id == user.id)
    )
    token_response = token_request.scalar_one_or_none()

    if not token_response:
        raise HTTPException(status_code=404, detail="Token not found")

    if token_response.token != activation_data.token:
        raise HTTPException(
            status_code=401, detail="Incorrect token or email address specified"
        )

    if datetime.now(timezone.utc) > token_response.expires_at.replace(
        tzinfo=timezone.utc
    ):
        await db.delete(token_response)
        await db.commit()
        raise HTTPException(status_code=401, detail="Token has expired")

    user.is_active = True
    await db.commit()
    await db.refresh(user)

    return MessageSchema(message="Account activated")


@router.post("/resend_activation", response_model=MessageSchema)
async def resend_activation(
    user_data: ResendActivationAccountSchema, db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_email(email=user_data.email, db=db)

    await check_user(user_data.email, db=db)

    activation_token = await create_activation_token(user_id=user.id, db=db)

    send_activation_email(user_email=user.email, token=activation_token.token)

    return MessageSchema(message="New activation token sent to your email")


@router.post("/login", response_model=UserLoginResponseSchema)
async def login(user_data: UserLoginRequestSchema, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(email=user_data.email, db=db)
    await check_user(user_data.email, db=db)

    check_password = verify_password(user_data.password, user.hashed_password)

    if not check_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token({"subject": user.email})
    refresh_token = create_refresh_token({"subject": user.email})

    check = await check_refresh_token(user_id=user.id, db=db)

    if check is None:
        try:
            new_refresh_token = RefreshToken(user_id=user.id, token=refresh_token)
            db.add(new_refresh_token)
            await db.commit()

        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while processing the request.",
            )

    return UserLoginResponseSchema(
        access_token=access_token, refresh_token=refresh_token
    )


@router.post("/logout", response_model=MessageSchema)
async def logout(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):

    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    email = payload.get("subject")
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user_by_email = await get_user_by_email(email=email, db=db)
    await check_user(user_by_email.email, db=db)

    request_token = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == user_by_email.id)
    )
    response_token = request_token.scalar_one_or_none()
    try:
        await db.delete(response_token)
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request.",
        )
    return MessageSchema(message="Logged out")


@router.post("/change_password", response_model=MessageSchema)
async def change_password(
    user_data: ChangePasswordRequestSchema, db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_email(email=user_data.email, db=db)
    await check_user(user_data.email, db=db)

    check_password = verify_password(user_data.password, user.hashed_password)

    if not check_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    hashed_password = hash_password(user_data.new_password)

    user.hashed_password = hashed_password
    await db.commit()

    return MessageSchema(message="Password changed")


@router.post("/forgot_password", response_model=MessageSchema)
async def forgot_password(email: EmailSchema, db: AsyncSession = Depends(get_db)):
    user_by_email = await get_user_by_email(email=email.email, db=db)
    await check_user(email=email.email, db=db)

    if user_by_email.is_active:

        request_token = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_by_email.id
            )
        )
        check_token_db = request_token.scalar_one_or_none()

        if not check_token_db:
            reset_token = PasswordResetToken(user_id=user_by_email.id)

            try:
                db.add(reset_token)
                await db.commit()
                await db.refresh(reset_token)
            except SQLAlchemyError:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An error occurred while processing the request.",
                )
            send_reset_password_email(user_email=email.email, token=reset_token.token)

        send_reset_password_email(user_email=email.email, token=check_token_db.token)

        return MessageSchema(message="Token for reset password email sent")


@router.post("/reset_password", response_model=MessageSchema)
async def reset_password(
    new_password_data: ResetPasswordSchema, db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_email(email=new_password_data.email, db=db)
    await check_user(new_password_data.email, db=db)

    token_request = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )
    token_response = token_request.scalar_one_or_none()

    if token_response.token != new_password_data.token:
        raise HTTPException(status_code=401, detail="Invalid token or email")

    validate_password_strength(new_password_data.new_password)

    new_password = hash_password(new_password_data.password)
    user.hashed_password = new_password

    await db.delete(token_response)
    await db.commit()

    return MessageSchema(message="Password changed")


@router.post("/refresh_access_token", response_model=AccessTokenSchema)
async def refresh_access_token(
    token: RefreshTokenSchema, db: AsyncSession = Depends(get_db)
):
    refresh_token_request = await db.execute(
        select(RefreshToken).where(RefreshToken.token == token.refresh_token)
    )
    result = refresh_token_request.scalar_one_or_none()

    if not result:
        raise HTTPException(status_code=401, detail="Invalid token or email")

    if result.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        await delete_expired_refresh_token(token=result, db=db)
        raise HTTPException(status_code=401, detail="Expired token")

    create_token = create_access_token({"subject": result.user_id})

    return AccessTokenSchema(access_token=create_token)
