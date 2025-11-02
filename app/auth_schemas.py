from pydantic import BaseModel, Field

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenRequest(BaseModel):
    email: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class OAuth2AuthRequest(BaseModel):
    state: str
    code_verifier: str
    provider: str = "bank"

class OAuthCallbackResponse(BaseModel):
    authorization_code: str
    state: str
