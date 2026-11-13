from typing import Annotated

from pydantic import BaseModel, Field, SecretStr

from app.schemas.entities import InputModel


class LoginInput(InputModel):
    username: str = Field(min_length=1, max_length=100)
    password: Annotated[SecretStr, Field(min_length=1, max_length=1024)]


class PasswordChange(InputModel):
    current_password: Annotated[SecretStr, Field(min_length=1, max_length=1024)]
    new_password: Annotated[SecretStr, Field(min_length=8, max_length=1024)]


class UserRead(BaseModel):
    id: int
    username: str


class LoginRead(BaseModel):
    user: UserRead


class AuthStatus(BaseModel):
    configured: bool
