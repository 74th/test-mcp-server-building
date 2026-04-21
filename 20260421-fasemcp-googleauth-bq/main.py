import csv
import json
import logging
import os
from datetime import datetime, timezone
from io import StringIO
from typing import Any
from urllib import error, request

from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider
from fastmcp.server.dependencies import get_access_token

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


def execute_bigquery_jobs_query(access_token: Any, query_text: str) -> dict[str, Any]:
    payload = json.dumps(
        {
            "query": query_text,
            "useLegacySql": False,
            "timeoutMs": 30000,
        }
    ).encode("utf-8")
    http_request = request.Request(
        url=f"https://bigquery.googleapis.com/bigquery/v2/projects/{BIGQUERY_PROJECT}/queries",
        data=payload,
        headers={
            "Authorization": f"Bearer {access_token.token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with request.urlopen(http_request) as response:
        return json.loads(response.read().decode("utf-8"))


def stringify_bigquery_value(field: dict[str, Any], value: Any) -> str:
    if value is None:
        return ""

    field_type = field.get("type")
    field_mode = field.get("mode")

    if field_mode == "REPEATED":
        repeated_values = [
            stringify_bigquery_value({**field, "mode": "NULLABLE"}, item.get("v"))
            for item in value
        ]
        return json.dumps(repeated_values, ensure_ascii=False)

    if field_type == "RECORD":
        nested_fields = field.get("fields") or []
        nested_values = value.get("f") or []
        record = {
            nested_field.get("name") or str(index): stringify_bigquery_value(
                nested_field,
                nested_value.get("v"),
            )
            for index, (nested_field, nested_value) in enumerate(
                zip(nested_fields, nested_values, strict=False)
            )
        }
        return json.dumps(record, ensure_ascii=False)

    if field_type == "TIMESTAMP":
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
        except (TypeError, ValueError):
            return str(value)

    if field_type == "BOOL":
        return str(value).lower()

    return str(value)


def format_jobs_query_result_as_csv(result: dict[str, Any]) -> str:
    schema_fields = result.get("schema", {}).get("fields") or []
    rows = result.get("rows") or []

    output = StringIO()
    writer = csv.writer(output)

    if not schema_fields:
        return output.getvalue()

    writer.writerow([field.get("name") or "column" for field in schema_fields])
    for row in rows:
        fields = row.get("f") or []
        writer.writerow(
            [
                stringify_bigquery_value(field, cell.get("v"))
                for field, cell in zip(schema_fields, fields, strict=False)
            ]
        )
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
        result = execute_bigquery_jobs_query(access_token, BIGQUERY_QUERY)
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.exception(
            "BigQuery jobs.query failed for %s: %s",
            identity,
            error_body,
        )
        return "bigquery query failed"
    except Exception:
        logger.exception("BigQuery query failed for %s", identity)
        return "bigquery query failed"

    if not result.get("jobComplete", True):
        logger.warning("BigQuery jobs.query did not complete in time for %s", identity)
        return "bigquery query did not complete"

    if result.get("errors"):
        logger.error("BigQuery jobs.query returned errors for %s: %s", identity, result["errors"])
        return "bigquery query failed"

    logger.info(
        "BigQuery query succeeded for %s (%s): %d rows",
        identity,
        name or "unknown",
        len(result.get("rows") or []),
    )
    return format_jobs_query_result_as_csv(result)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
