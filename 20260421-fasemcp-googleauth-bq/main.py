import csv
import logging
import os
from io import StringIO
from typing import Any, cast

from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider
from fastmcp.server.dependencies import get_access_token
from google.cloud import bigquery
from google.cloud.bigquery.table import Row
from google.oauth2.credentials import Credentials

LOG_LEVEL_NAME = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)
logging.basicConfig(level=LOG_LEVEL)
logging.getLogger().setLevel(LOG_LEVEL)
logger = logging.getLogger(__name__)

BASE_URL = os.environ["BASE_URL"]
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
# BIGQUERY_SCOPE = "https://www.googleapis.com/auth/bigquery"
BIGQUERY_SCOPE = "https://www.googleapis.com/auth/bigquery.readonly"
BIGQUERY_PROJECT = "nnyn-dev"
BIGQUERY_QUERY = """
SELECT timestamp, co2_mhz19c
FROM `nnyn-dev.house_monitor.co2`
WHERE TIMESTAMP_TRUNC(timestamp, DAY) = TIMESTAMP("2022-11-07")
LIMIT 10
""".strip()


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
        BIGQUERY_SCOPE,
    ],
    extra_authorize_params={
        "access_type": "offline",
        "prompt": "consent",
    },
)

mcp = FastMCP("google-auth-mcp", auth=auth)


def get_authenticated_access_token() -> Any | None:
    return get_access_token()


def get_authenticated_identity(access_token: Any) -> tuple[str, str | None]:
    claims = access_token.claims or {}
    upstream_claims = claims.get("upstream_claims") or {}
    email = claims.get("email") or upstream_claims.get("email")
    name = claims.get("name") or upstream_claims.get("name")
    subject = claims.get("sub") or upstream_claims.get("sub") or access_token.client_id

    return email or subject, name


def build_bigquery_client(access_token: Any) -> bigquery.Client:
    credentials = Credentials(token=access_token.token, scopes=[BIGQUERY_SCOPE])
    return bigquery.Client(project=BIGQUERY_PROJECT, credentials=credentials)


def format_rows_as_csv(rows: list[Row]) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "co2_mhz19c"])
    for row in rows:
        writer.writerow([row["timestamp"].isoformat(), row["co2_mhz19c"]])
    return output.getvalue()


@mcp.tool
def whoami() -> str:
    access_token = get_authenticated_access_token()
    if access_token is None:
        return "unauthenticated"

    identity, name = get_authenticated_identity(access_token)
    if name and name != identity:
        return f"authenticated as {name} <{identity}>"
    return f"authenticated as {identity}"


@mcp.tool
def query() -> str:
    access_token = get_authenticated_access_token()
    if access_token is None:
        return "unauthenticated"

    identity, name = get_authenticated_identity(access_token)

    try:
        client = build_bigquery_client(access_token)
        rows = cast(list[Row], list(client.query(BIGQUERY_QUERY).result()))
    except Exception:
        logger.exception("BigQuery query failed for %s", identity)
        return "bigquery query failed"

    logger.info(
        "BigQuery query succeeded for %s (%s): %d rows",
        identity,
        name or "unknown",
        len(rows),
    )
    return format_rows_as_csv(rows)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
