from pydantic import BaseModel, EmailStr


class BaseUser(BaseModel):
    email: EmailStr
    password: str


class UserReadSchema(BaseModel):
    id: int
    email: EmailStr


class UserRegisterSchema(BaseUser):
    pass


class UserLoginRequestSchema(BaseUser):
    pass


class UserLoginResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
