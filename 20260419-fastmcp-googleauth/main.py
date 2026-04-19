import os

from fastmcp import FastMCP
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier

BASE_URL = os.environ["BASE_URL"]  # 例: https://mcp.example.com
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]

# Google 用トークン検証
# audience は通常、Google OAuth クライアント ID に合わせる
token_verifier = JWTVerifier(
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    issuer="https://accounts.google.com",
    audience=GOOGLE_CLIENT_ID,
    required_scopes=[
        "openid",
        "email",
        "profile",
    ],
)

auth = OAuthProxy(
    upstream_authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
    upstream_token_endpoint="https://oauth2.googleapis.com/token",
    upstream_client_id=GOOGLE_CLIENT_ID,
    upstream_client_secret=GOOGLE_CLIENT_SECRET,
    token_verifier=token_verifier,
    base_url=BASE_URL,

    # 必要なら明示
    # redirect_path="/auth/callback",

    # Google/OIDC 系では追加で scope を要求
    extra_authorize_params={
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    },
)

mcp = FastMCP("google-auth-mcp", auth=auth)

@mcp.tool
def whoami() -> str:
    return "authenticated"

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
