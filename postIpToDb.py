import sys
import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="1234",
        database="db1"
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
