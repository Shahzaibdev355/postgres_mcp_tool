from database.connection import get_postgres_connection


try:
    conn = get_postgres_connection()
    print("PostgreSQL connection successful!")

    conn.close()
    print("Connection closed.")

except Exception as e:
    print("Connection failed:", e)