import http
from typing import Any
import httpx  # async client
from mcp.server.fastmcp import FastMCP
from database.connection import get_postgres_connection

# initilize fastMCP server
mcp = FastMCP(name="postgres_mcp", host="0.0.0.0", port=8000)

USER_AGENT = "postgres_mcp_app/1.0"


async def make_conn_request(url: str) -> dict[str, Any] | None:
    """Make a req to connect with postgres"""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()

        except Exception:
            return None


@mcp.tool()
def postgres_connection() -> str:
    try:
        conn = get_postgres_connection()
        conn.close()

        return "PostgreSQL connection successful!"

    except Exception as e:
        return f"PostgreSQL connection failed: {e}"


@mcp.tool()
def list_schemas() -> str:
    """List all schemas in the connected PostgreSQL db"""

    try:
        conn = get_postgres_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT schema_name FROM information_schema.schemata
             WHERE schema_name NOT IN ('pg_catalog', 'information_schema');
        """
        )

        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return "No schemas found."

        return "\n".join(schema[0] for schema in rows)

    except Exception as e:
        return f"Failed to list schemas: {e}"
