from typing import Any
from mcp.server.fastmcp import FastMCP

from database.connection import (get_postgres_connection)



def register_query_tools(mcp: FastMCP):
    @mcp.tool()
    def execute_select(query: str) -> str:
        """Execute a read-only SELECT query on the PostgreSQL database."""
        try:
            # Basic safety check
            if not query.strip().lower().startswith("select"):
                return "Only SELECT queries are allowed."

            conn = get_postgres_connection()
            cur = conn.cursor()

            cur.execute(query)
            rows = cur.fetchall()

            # Get column names
            columns = [desc[0] for desc in cur.description]

            cur.close()
            conn.close()

            if not rows:
                return "Query returned no results."

            # Format output
            result = [" | ".join(columns)]

            for row in rows:
                result.append(" | ".join(str(value) for value in row))

            return "\n".join(result)

        except Exception as e:
            return f"Query failed: {e}"