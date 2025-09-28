from pydantic import BaseModel, EmailStr

class RefreshTokenSchema(BaseModel):
    refresh_token: str

class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str


class ForgotPasswordSchema(BaseModel):
    email: EmailStr

class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str

