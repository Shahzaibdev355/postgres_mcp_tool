from typing import Any
import httpx  # async client
from mcp.server.fastmcp import FastMCP
from database.connection import get_postgres_connection
from psycopg2 import sql
import json


# for column add
ALLOWED_TYPES = {
    "TEXT",
    "VARCHAR",
    "INT",
    "INTEGER",
    "BIGINT",
    "SMALLINT",
    "BOOLEAN",
    "DATE",
    "TIMESTAMP",
    "NUMERIC",
    "REAL",
    "DOUBLE PRECISION",
    "SERIAL",
}


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
def insert_row(
    schema: str,
    table: str,
    columns: str,  # JSON array string, e.g. ["name","age"]
    values: str,  # JSON array string, e.g. ["Ali", 25]
) -> str:
    """Insert a row into any PostgreSQL table.
    columns and values must be JSON array strings, e.g.
    columns = '["name","age"]', values = '["Ali", 25]'
    """

    try:
        try:
            columns_list = json.loads(columns)
            values_list = json.loads(values)
        except json.JSONDecodeError as e:
            return f"Invalid JSON for columns/values: {e}"

        if not isinstance(columns_list, list) or not isinstance(values_list, list):
            return "columns and values must be JSON arrays."

        if len(columns_list) != len(values_list):
            return "Number of columns must match number of values."

        conn = get_postgres_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_name = %s
            """,
            (schema, table),
        )

        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return f"Table '{schema}.{table}' does not exist."

        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
            """,
            (schema, table),
        )

        existing_columns = {row[0] for row in cur.fetchall()}
        invalid_columns = set(columns_list) - existing_columns

        if invalid_columns:
            cur.close()
            conn.close()
            return f"Invalid columns: {', '.join(invalid_columns)}"

        placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in values_list)

        query = sql.SQL(
            """
            INSERT INTO {}.{} ({})
            VALUES ({})
        """
        ).format(
            sql.Identifier(schema),
            sql.Identifier(table),
            sql.SQL(", ").join(sql.Identifier(c) for c in columns_list),
            placeholders,
        )

        cur.execute(query, values_list)
        conn.commit()

        cur.close()
        conn.close()

        return f"Row inserted successfully into {schema}.{table}."

    except Exception as e:
        return f"Failed to insert row: {e}"


@mcp.tool()
def add_column(schema: str, table: str, column: str, data_type: str) -> str:
    """Add a new column to an existing PostgreSQL table.
    data_type must be one of: TEXT, VARCHAR, INT, INTEGER, BIGINT,
    SMALLINT, BOOLEAN, DATE, TIMESTAMP, NUMERIC, REAL, DOUBLE PRECISION, SERIAL
    """

    try:
        data_type_clean = data_type.strip().upper()

        if data_type_clean not in ALLOWED_TYPES:
            return f"Invalid data type '{data_type}'. Allowed: {', '.join(sorted(ALLOWED_TYPES))}"

        conn = get_postgres_connection()
        cur = conn.cursor()

        # check table exists
        cur.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_name = %s
            """,
            (schema, table),
        )

        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return f"Table '{schema}.{table}' does not exist."

        # check column doesn't already exist
        cur.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
              AND column_name = %s
            """,
            (schema, table, column),
        )

        if cur.fetchone() is not None:
            cur.close()
            conn.close()
            return f"Column '{column}' already exists in {schema}.{table}."

        query = sql.SQL("ALTER TABLE {}.{} ADD COLUMN {} " + data_type_clean).format(
            sql.Identifier(schema),
            sql.Identifier(table),
            sql.Identifier(column),
        )

        cur.execute(query)
        conn.commit()

        cur.close()
        conn.close()

        return f"Column '{column}' ({data_type_clean}) added to {schema}.{table}."

    except Exception as e:
        return f"Failed to add column: {e}"




@mcp.tool()
def update_row(
    schema: str,
    table: str,
    columns: str,  # JSON array string, e.g. ["age"]
    values: str,  # JSON array string, e.g. [25]
    where_column: str,  # column to match on, e.g. "id"
    where_value: str,  # value to match, e.g. "1"
) -> str:
    """Update a row in any PostgreSQL table, matched by one column.
    columns and values must be JSON array strings, e.g.
    columns = '["age"]', values = '[25]'
    where_column = "id", where_value = "1"
    """

    try:
        try:
            columns_list = json.loads(columns)
            values_list = json.loads(values)
        except json.JSONDecodeError as e:
            return f"Invalid JSON for columns/values: {e}"

        if not isinstance(columns_list, list) or not isinstance(values_list, list):
            return "columns and values must be JSON arrays."

        if len(columns_list) != len(values_list):
            return "Number of columns must match number of values."

        if not columns_list:
            return "At least one column must be provided to update."

        conn = get_postgres_connection()
        cur = conn.cursor()

        # check table exists
        cur.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_name = %s
            """,
            (schema, table),
        )

        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return f"Table '{schema}.{table}' does not exist."

        # check all columns exist (including where_column)
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
            """,
            (schema, table),
        )

        existing_columns = {row[0] for row in cur.fetchall()}
        invalid_columns = set(columns_list) - existing_columns

        if invalid_columns:
            cur.close()
            conn.close()
            return f"Invalid columns: {', '.join(invalid_columns)}"

        if where_column not in existing_columns:
            cur.close()
            conn.close()
            return f"Invalid where_column: '{where_column}' does not exist in {schema}.{table}."

        # check the target row actually exists
        check_query = sql.SQL("SELECT 1 FROM {}.{} WHERE {} = %s").format(
            sql.Identifier(schema),
            sql.Identifier(table),
            sql.Identifier(where_column),
        )
        cur.execute(check_query, (where_value,))

        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return f"No row found where {where_column} = {where_value}."

        # build SET clause
        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(c)) for c in columns_list
        )

        query = sql.SQL("UPDATE {}.{} SET {} WHERE {} = %s").format(
            sql.Identifier(schema),
            sql.Identifier(table),
            set_clause,
            sql.Identifier(where_column),
        )

        cur.execute(query, values_list + [where_value])
        conn.commit()

        rows_affected = cur.rowcount

        cur.close()
        conn.close()

        return f"{rows_affected} row(s) updated in {schema}.{table} where {where_column} = {where_value}."

    except Exception as e:
        return f"Failed to update row: {e}"
