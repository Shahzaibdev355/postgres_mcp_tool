from typing import Any
from mcp.server.fastmcp import FastMCP
import psycopg2


from database.connection import (
    set_active_connection,
    clear_active_connection,
    get_active_connection_info,
)


def register_database_tools(mcp: FastMCP):
    @mcp.tool()
    def connect_database(connection_string: str) -> str:
        """Connect to a different PostgreSQL database using a full connection string.
        Format: postgresql://user:password@host:port/dbname

        This overrides the default .env connection for the rest of this session.
        Use disconnect_database to revert back to the default .env connection.
        """
        try:
            # test the connection before committing to it
            test_conn = psycopg2.connect(connection_string)
            test_conn.close()

            set_active_connection(connection_string)
            return "Successfully connected to the new database. All future operations will use this connection."

        except Exception as e:
            return f"Failed to connect with the given connection string: {e}"


    @mcp.tool()
    def disconnect_database() -> str:
        """Revert back to the default .env-configured PostgreSQL connection."""
        clear_active_connection()
        return "Reverted to default .env connection."


    @mcp.tool()
    def current_connection_info() -> str:
        """Show which database connection is currently active."""
        return get_active_connection_info()
