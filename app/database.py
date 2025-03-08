import mysql.connector
from mysql.connector import pooling
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'store_monitoring'),
}

# Create connection pool
connection_pool = pooling.MySQLConnectionPool(
    pool_name="store_monitoring_pool",
    pool_size=5,
    **DB_CONFIG
)

def get_connection():
    """Get a connection from the pool"""
    return connection_pool.get_connection()

def execute_query(query, params=None, fetch=False):
    """Execute a query and optionally fetch results"""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        if fetch:
            return cursor.fetchall()
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        raise e
    finally:
        cursor.close()
        connection.close() 