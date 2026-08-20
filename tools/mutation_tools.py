from typing import Any
from mcp.server.fastmcp import FastMCP
from psycopg2 import sql
import json


from database.connection import get_postgres_connection


def register_mutation_tools(mcp: FastMCP):
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


    @mcp.tool()
    def delete_row(
        schema: str,
        table: str,
        where_column: str,
        where_value: str,
    ) -> str:
        """Delete row(s) from a table, matched by one column.
        where_column = "id", where_value = "1"
        """

        try:
            conn = get_postgres_connection()
            cur = conn.cursor()

            # check table exists
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
                return f"Table '{schema}.{table}' does not exist."

            # check where_column exists
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                """,
                (schema, table),
            )
            existing_columns = {row[0] for row in cur.fetchall()}
            if where_column not in existing_columns:
                cur.close()
                conn.close()
                return f"Invalid where_column: '{where_column}' does not exist in {schema}.{table}."

            # check row exists
            check_query = sql.SQL("SELECT 1 FROM {}.{} WHERE {} = %s").format(
                sql.Identifier(schema), sql.Identifier(table), sql.Identifier(where_column)
            )
            cur.execute(check_query, (where_value,))
            if cur.fetchone() is None:
                cur.close()
                conn.close()
                return f"No row found where {where_column} = {where_value}."

            # how many rows will this affect? warn if more than 1
            count_query = sql.SQL("SELECT COUNT(*) FROM {}.{} WHERE {} = %s").format(
                sql.Identifier(schema), sql.Identifier(table), sql.Identifier(where_column)
            )
            cur.execute(count_query, (where_value,))
            match_count = cur.fetchone()[0]

            delete_query = sql.SQL("DELETE FROM {}.{} WHERE {} = %s").format(
                sql.Identifier(schema), sql.Identifier(table), sql.Identifier(where_column)
            )

            try:
                cur.execute(delete_query, (where_value,))
            except Exception as fk_err:
                conn.rollback()
                cur.close()
                conn.close()
                return (
                    f"Cannot delete: row(s) are referenced by a foreign key in another table. "
                    f"Details: {fk_err}"
                )

            conn.commit()
            rows_affected = cur.rowcount
            cur.close()
            conn.close()

            return f"{rows_affected} row(s) deleted from {schema}.{table} where {where_column} = {where_value}."

        except Exception as e:
            return f"Failed to delete row: {e}"
