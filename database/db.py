import mysql.connector
from mysql.connector import Error
from ..config import Config

def get_db_connection():
    """
    Create and return a database connection
    """

    # Validate username
    if not Config.DB_USER:
        raise ValueError("Database username is required")

    try:
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            port=Config.DB_PORT
        )

        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        raise

def test_connection():
    """
    Test database connection
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        db_name = cursor.fetchone()
        print(f"Successfully connected to database: {db_name[0]}")
        cursor.close()
        conn.close()
        return True
    except ValueError as ve:
        print(f"Configuration error: {ve}")
        return False
    except Error as e:
        print(f"Database connection test failed: {e}")
        return False