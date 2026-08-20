from typing import Any
import httpx  # async client
from mcp.server.fastmcp import FastMCP


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


# import tool modules so they register
from tools.schema_tools import register_schema_tools
from tools.query_tools import register_query_tools
from tools.mutation_tools import register_mutation_tools
from tools.database_tools import register_database_tools

register_schema_tools(mcp)
register_query_tools(mcp)
register_mutation_tools(mcp)
register_database_tools(mcp)


# @mcp.tool()
# def postgres_connection() -> str:
#     try:
#         conn = get_postgres_connection()
#         conn.close()

#         return "PostgreSQL connection successful!"

#     except Exception as e:
#         return f"PostgreSQL connection failed: {e}"
