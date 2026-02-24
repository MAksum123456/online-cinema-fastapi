from pydantic import BaseModel, EmailStr


class ActivationAccountSchema(BaseModel):
    email: EmailStr
    token: str


class EmailSchema(BaseModel):
    email: EmailStr


class ResendActivationAccountSchema(EmailSchema):
    pass


class ChangePasswordRequestSchema(BaseModel):
    email: EmailStr
    password: str
    new_password: str


class ResetPasswordSchema(EmailSchema):
    password: str
    token: str


class MessageSchema(BaseModel):
    message: str


class RefreshTokenSchema(BaseModel):
    refresh_token: str


class AccessTokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
