# import psycopg2
# from config import settings

# # Holds a dynamically-set connection string for this server session
# _active_connection_string: str | None = None


# def set_active_connection(connection_string: str) -> None:
#     global _active_connection_string
#     _active_connection_string = connection_string


# def clear_active_connection() -> None:
#     global _active_connection_string
#     _active_connection_string = None


# def get_active_connection_info() -> str:
#     if _active_connection_string:
#         return "Using custom connection string (session override)."
#     return f"Using default .env connection: {settings.POSTGRES_DB}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}"


# def get_postgres_connection():
#     if _active_connection_string:
#         return psycopg2.connect(_active_connection_string)

#     return psycopg2.connect(
#         host=settings.POSTGRES_HOST,
#         port=settings.POSTGRES_PORT,
#         database=settings.POSTGRES_DB,
#         user=settings.POSTGRES_USER,
#         password=settings.POSTGRES_PASSWORD,
#     )


import psycopg2

# Holds the active connection string for this server session
_active_connection_string: str | None = None


def set_active_connection(connection_string: str) -> None:
    global _active_connection_string
    _active_connection_string = connection_string


def clear_active_connection() -> None:
    global _active_connection_string
    _active_connection_string = None


def get_active_connection_info() -> str:
    if _active_connection_string:
        return "Using custom connection string (session override)."

    return "No active database connection."


def get_postgres_connection():
    if not _active_connection_string:
        raise RuntimeError(
            "No active database connection. "
            "Please connect to a PostgreSQL database first."
        )

    return psycopg2.connect(_active_connection_string)
