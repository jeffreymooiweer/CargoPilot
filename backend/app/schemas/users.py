from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    role: UserRole | None = None
    active: bool | None = None
    # An administrator setting a new password for someone who lost theirs.
    # Unlike PasswordChange there is no current_password: the admin does
    # not know it, which is the whole reason for the reset.
    password: str | None = Field(default=None, min_length=8)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: UserRole
    active: bool


class PasswordResetRequest(BaseModel):
    """Who forgot their password. A user name or an address — both are what
    people remember, and the answer is the same either way."""

    identifier: str = Field(default="", max_length=254)


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=16, max_length=256)
    new_password: str = Field(min_length=8)
