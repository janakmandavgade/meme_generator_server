from pydantic import BaseModel, Field, EmailStr, SecretStr


class User(BaseModel):
    email: EmailStr = Field(..., example="example@email.com")
    password: SecretStr = Field(..., min_length=8, example="password123")


