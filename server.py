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


@mcp.tool()
def list_tables() -> str:
    """List all tables in the connected PostgreSQL database"""
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
              AND table_schema NOT IN ('pg_catalog', 'information_schema')
        """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return "No tables found."

        return "\n".join(f"{schema}.{table}" for schema, table in rows)

    except Exception as e:
        return f"Failed to list tables: {e}"


@mcp.tool()
def describe_table(schema: str, table: str) -> str:
    """describe table in the connected PostgreSQL database"""
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = %s
            ORDER BY ordinal_position;
        """,
            (schema, table),
        )

        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return "No table schema found."

        return "\n".join(
            f"{column} | {data_type} | {nullable}"
            for column, data_type, nullable in rows
        )

    except Exception as e:
        return f"Failed to list table schema: {e}"


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


@mcp.tool()
def insert_row(schema: str, table: str, name: str) -> str:
    """Insert a name into a table."""

    try:
        conn = get_postgres_connection()
        cur = conn.cursor()

        # check schema + table exist
        cur.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        """,
            (schema, table),
        )

        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return f"Schema or table '{schema}.{table}' does not exist"

        query = f"""
            INSERT INTO {schema}.{table} (name)
            VALUES (%s)
        """

        cur.execute(query, (name,))
        conn.commit()

        cur.close()
        conn.close()

        return f"'{name}' inserted successfully into {schema}.{table}"

    except Exception as e:
        return f"failed to insert row: {e}"
