import sys
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()
SQL_HOST = os.getenv("SQL_HOST")
SQL_USER = os.getenv("SQL_USER")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")
SQL_DATABASE = os.getenv("SQL_DATABASE")

def get_db_connection():
    return mysql.connector.connect(
        host= SQL_HOST,
        user= SQL_USER,
        password= SQL_PASSWORD,
        database= SQL_DATABASE
    )

MODEL_NAME = sys.argv[1]
IP = sys.argv[2]

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

cursor.execute("""
    UPDATE models
    SET modelIp = %s
    WHERE modelName = %s
""", (IP, MODEL_NAME))

conn.commit()
cursor.close()
conn.close()

print(f"✅ IP {IP} for model '{MODEL_NAME}' stored in database.")
