import os
import mysql.connector
from mysql.connector import Error

# Database configuration for PythonAnywhere
DB_HOST = 'Ppadak2005jitu.mysql.pythonanywhere-services.com'
DB_NAME = 'Ppadak2005jitu$heritage'
DB_USER = 'Ppadak2005jitu'
DB_PASSWORD = 'Cb2q64Jj'
DB_PORT = '3306'

WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=int(DB_PORT)
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None