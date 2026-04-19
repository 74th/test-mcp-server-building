import logging
import os
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider
from fastmcp.server.dependencies import get_access_token

LOG_LEVEL_NAME = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)
logging.basicConfig(level=LOG_LEVEL)
logging.getLogger().setLevel(LOG_LEVEL)
logger = logging.getLogger(__name__)

BASE_URL = os.environ["BASE_URL"]  # 例: https://mcp.example.com
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]


class LoggingGoogleProvider(GoogleProvider):
    async def _extract_upstream_claims(
        self, idp_tokens: dict[str, Any]
    ) -> dict[str, Any] | None:
        access_token = idp_tokens.get("access_token")
        if not access_token:
            logger.warning("Google token response did not include an access_token")
            return None

        verified = await self._token_validator.verify_token(access_token)
        if not verified:
            logger.warning("Google access token verification failed during login")
            return None

        claims = dict(verified.claims or {})
        logger.info(
            "Google authentication succeeded: email=%s name=%s sub=%s",
            claims.get("email") or "unknown",
            claims.get("name") or "unknown",
            claims.get("sub") or "unknown",
        )
        return claims


auth = LoggingGoogleProvider(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    base_url=BASE_URL,
    required_scopes=[
        "openid",
        "email",
        "profile",
    ],
    extra_authorize_params={
        "access_type": "offline",
        "prompt": "consent",
    },
)

mcp = FastMCP("google-auth-mcp", auth=auth)


@mcp.tool
def whoami() -> str:
    access_token = get_access_token()
    if access_token is None:
        return "unauthenticated"

    claims = access_token.claims or {}
    upstream_claims = claims.get("upstream_claims") or {}
    email = claims.get("email") or upstream_claims.get("email")
    name = claims.get("name") or upstream_claims.get("name")
    subject = claims.get("sub") or upstream_claims.get("sub") or access_token.client_id

    identity = email or subject
    if name and name != identity:
        return f"authenticated as {name} <{identity}>"
    return f"authenticated as {identity}"


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
